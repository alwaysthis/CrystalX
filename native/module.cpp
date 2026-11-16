#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "kernels.hpp"
#include <cmath>
#include <limits>
#include <stdexcept>

namespace {
struct Ref {
    PyObject* p;
    explicit Ref(PyObject* value):p(value) { if(!p) throw std::runtime_error("Python conversion failed"); }
    ~Ref() { Py_DECREF(p); }
    Ref(const Ref&)=delete;
};
struct ReleaseGIL {
    PyThreadState* state=PyEval_SaveThread();
    ~ReleaseGIL() { PyEval_RestoreThread(state); }
};
double number(PyObject* value) {
    double v=PyFloat_AsDouble(value);
    if(PyErr_Occurred()) throw std::runtime_error("Expected a number");
    if(!std::isfinite(v)) throw std::invalid_argument("Expected finite values");
    return v;
}
int index(PyObject* value) {
    long v=PyLong_AsLong(value);
    if(PyErr_Occurred()) throw std::runtime_error("Expected an integer");
    if(v<0 || v>std::numeric_limits<int>::max()) throw std::invalid_argument("Invalid species ID");
    return static_cast<int>(v);
}
crystalx::Vec vector(PyObject* value) {
    Ref seq(PySequence_Fast(value,"Expected a vector"));
    if(PySequence_Fast_GET_SIZE(seq.p)!=3) throw std::invalid_argument("Expected three vector components");
    crystalx::Vec result;
    for(int i=0;i<3;++i) result[i]=number(PySequence_Fast_GET_ITEM(seq.p,i));
    return result;
}
PyObject* failure(const std::exception& error) {
    if(!PyErr_Occurred()) PyErr_SetString(PyExc_ValueError,error.what());
    return nullptr;
}
bool valid_material(double r,double g,double b,double roughness,double ior,double gloss) {
    for(double v:{r,g,b,roughness,gloss}) if(!std::isfinite(v) || v<0 || v>1) {
        PyErr_SetString(PyExc_ValueError,"RGB, roughness and gloss must be in [0,1]"); return false;
    }
    if(!std::isfinite(ior) || ior<1 || ior>3) { PyErr_SetString(PyExc_ValueError,"IOR must be in [1,3]"); return false; }
    return true;
}
PyObject* sphere(PyObject*,PyObject* args) {
    double r,g,b,roughness,ior,gloss;
    if(!PyArg_ParseTuple(args,"dddddd",&r,&g,&b,&roughness,&ior,&gloss)) return nullptr;
    if(!valid_material(r,g,b,roughness,ior,gloss)) return nullptr;
    PyObject* pixels=PyBytes_FromStringAndSize(nullptr,128*128*4); if(!pixels) return nullptr;
    auto* data=reinterpret_cast<std::uint8_t*>(PyBytes_AS_STRING(pixels));
    { ReleaseGIL release; crystalx::sphere_pixels(r,g,b,roughness,ior,gloss,data); }
    return pixels;
}
PyObject* cylinder(PyObject*,PyObject* args) {
    double nx,ny,r,g,b,roughness,ior,gloss;
    if(!PyArg_ParseTuple(args,"dddddddd",&nx,&ny,&r,&g,&b,&roughness,&ior,&gloss)) return nullptr;
    if(!std::isfinite(nx) || !std::isfinite(ny)) { PyErr_SetString(PyExc_ValueError,"Expected finite normal"); return nullptr; }
    if(!valid_material(r,g,b,roughness,ior,gloss)) return nullptr;
    std::array<crystalx::Vec,33> colors;
    { ReleaseGIL release; colors=crystalx::cylinder_colors(nx,ny,r,g,b,roughness,ior,gloss); }
    PyObject* result=PyTuple_New(33); if(!result) return nullptr;
    for(int i=0;i<33;++i) {
        PyObject* row=Py_BuildValue("(ddd)",colors[i][0],colors[i][1],colors[i][2]);
        if(!row) { Py_DECREF(result); return nullptr; }
        PyTuple_SET_ITEM(result,i,row);
    }
    return result;
}
PyObject* bonds(PyObject*,PyObject* args) {
    PyObject *lat,*pos,*ids,*rs,*margin; double cutoff;
    if(!PyArg_ParseTuple(args,"OOOOOd",&lat,&pos,&ids,&rs,&margin,&cutoff)) return nullptr;
    try {
        if(!std::isfinite(cutoff) || cutoff<=0) throw std::invalid_argument("Expected positive cutoff");
        Ref lattice(PySequence_Fast(lat,"Expected lattice rows"));
        if(PySequence_Fast_GET_SIZE(lattice.p)!=3) throw std::invalid_argument("Expected 3x3 lattice");
        crystalx::Lattice cell;
        for(int i=0;i<3;++i) cell[i]=vector(PySequence_Fast_GET_ITEM(lattice.p,i));
        Ref positions(PySequence_Fast(pos,"Expected positions")); Ref elements(PySequence_Fast(ids,"Expected species IDs"));
        auto n=PySequence_Fast_GET_SIZE(positions.p);
        if(n!=PySequence_Fast_GET_SIZE(elements.p) || n>std::numeric_limits<int>::max()) throw std::invalid_argument("Positions/species length mismatch");
        std::vector<crystalx::Vec> points; std::vector<int> species;
        points.reserve(n); species.reserve(n);
        for(Py_ssize_t i=0;i<n;++i) {
            auto point=vector(PySequence_Fast_GET_ITEM(positions.p,i));
            // Python's tiny-negative % 1 may round to exactly 1.0.
            for(double v:point) if(v<0 || v>1) throw std::invalid_argument("Expected wrapped fractional positions");
            points.push_back(point); species.push_back(index(PySequence_Fast_GET_ITEM(elements.p,i)));
        }
        Ref rules(PySequence_Fast(rs,"Expected rules")); std::vector<crystalx::Rule> bounds;
        for(Py_ssize_t i=0;i<PySequence_Fast_GET_SIZE(rules.p);++i) {
            Ref row(PySequence_Fast(PySequence_Fast_GET_ITEM(rules.p,i),"Expected rule tuple"));
            if(PySequence_Fast_GET_SIZE(row.p)!=4) throw std::invalid_argument("Expected four rule fields");
            bounds.push_back({index(PySequence_Fast_GET_ITEM(row.p,0)),index(PySequence_Fast_GET_ITEM(row.p,1)),
                number(PySequence_Fast_GET_ITEM(row.p,2)),number(PySequence_Fast_GET_ITEM(row.p,3))});
        }
        auto margins=vector(margin);
        for(double v:margins) if(v<0) throw std::invalid_argument("Expected nonnegative margins");
        crystalx::SearchResult result;
        { ReleaseGIL release; result=crystalx::search(cell,points,species,bounds,margins,cutoff); }
        Ref segments(PyList_New(0)); Ref matched(PyList_New(0));
        for(const auto& s:result.segments) {
            Ref row(Py_BuildValue("((ddd)(ddd)ii)",s.a[0],s.a[1],s.a[2],s.b[0],s.b[1],s.b[2],s.source,s.target));
            if(PyList_Append(segments.p,row.p)<0) return nullptr;
        }
        for(std::size_t i=0;i<result.matched.size();++i) if(result.matched[i]) {
            Ref value(PyLong_FromSize_t(i)); if(PyList_Append(matched.p,value.p)<0) return nullptr;
        }
        return PyTuple_Pack(2,segments.p,matched.p);
    } catch(const std::bad_alloc&) { return PyErr_NoMemory(); }
      catch(const std::exception& error) { return failure(error); }
}
PyMethodDef methods[]={
    {"cylinder_colors",cylinder,METH_VARARGS,"Return 33 cylinder RGB gradient samples."},
    {"sphere_pixels",sphere,METH_VARARGS,"Return 128x128 BGRA sphere pixels."},
    {"bond_candidates",bonds,METH_VARARGS,"Return clipped periodic candidates and matched rule indices."},
    {nullptr,nullptr,0,nullptr}
};
PyModuleDef definition={PyModuleDef_HEAD_INIT,"_native",nullptr,-1,methods};
}
PyMODINIT_FUNC PyInit__native() {
    PyObject* module=PyModule_Create(&definition);
    if(module && PyModule_AddIntConstant(module,"API_VERSION",2)<0) { Py_DECREF(module); return nullptr; }
    return module;
}
