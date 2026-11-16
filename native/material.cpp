#include "kernels.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>

namespace crystalx {
struct Sample { double nl, nv, nh; bool valid; };
static const auto samples=[] {
    std::array<Sample,128*128> values{};
    const double norm=std::sqrt(.36*.36+.44*.44+.82*.82);
    const double lx=-.36/norm, ly=.44/norm, lz=.82/norm;
    const double hn=std::sqrt(lx*lx+ly*ly+(lz+1)*(lz+1));
    for(int y=0;y<128;++y) for(int x=0;x<128;++x) {
        double nx=(x+.5-64)/64, ny=-(y+.5-64)/64, rr=nx*nx+ny*ny;
        if(rr>1) continue;
        double nz=std::sqrt(1-rr);
        values[y*128+x]={std::max(0.,nx*lx+ny*ly+nz*lz),nz,
            std::max(0.,(nx*lx+ny*ly+nz*(lz+1))/hn),true};
    }
    return values;
}();

static double linear(double v) { return v<=.04045 ? v/12.92 : std::pow((v+.055)/1.055,2.4); }
static double srgb(double v) {
    v=std::clamp(v,0.,1.);
    return v<=.0031308 ? v*12.92 : 1.055*std::pow(v,1/2.4)-.055;
}

namespace {
struct Surface {
    double a2,f,gloss;
    Surface(double roughness,double ior,double strength):gloss(strength) {
        const double alpha=std::max(.002,roughness*roughness); a2=alpha*alpha;
        const double norm=std::sqrt(.36*.36+.44*.44+.82*.82), lz=.82/norm;
        const double hz=(lz+1)/std::sqrt(2+2*lz), f0=std::pow((ior-1)/(ior+1),2);
        f=std::abs(ior-1)<1e-12 ? 0 : (f0+(1-f0)*std::pow(1-hz,5))*gloss;
    }
    std::array<double,2> operator()(double nl,double nv,double nh) const {
        nl=std::max(0.,nl); nv=std::max(.0001,nv); nh=std::max(0.,nh);
        const double diffuse=.2+.8*nl*(1-f);
        if(gloss==0 || nl<=0) return {diffuse,0};
        const double denom=nh*nh*(a2-1)+1;
        const double d=a2/(3.14159265358979323846*std::max(1e-14,denom*denom));
        const double gv=2*nv/(nv+std::sqrt(a2+(1-a2)*nv*nv));
        const double gl=2*nl/std::max(1e-12,nl+std::sqrt(a2+(1-a2)*nl*nl));
        return {diffuse,d*gv*gl*f/(4*nv)};
    }
};
}

void sphere_pixels(double r,double g,double b,double roughness,double ior,double gloss,std::uint8_t* pixels) {
    const double colors[]={linear(b),linear(g),linear(r)};
    const Surface shader(roughness,ior,gloss);
    for(int i=0;i<128*128;++i) {
        if(!samples[i].valid) { for(int c=0;c<4;++c) pixels[i*4+c]=0; continue; }
        const auto s=samples[i]; const auto terms=shader(s.nl,s.nv,s.nh);
        for(int c=0;c<3;++c) pixels[i*4+c]=static_cast<std::uint8_t>(std::nearbyint(srgb(colors[c]*terms[0]+terms[1])*255));
        pixels[i*4+3]=255;
    }
}

std::array<Vec,33> cylinder_colors(double normal_x,double normal_y,double r,double g,double b,
                                  double roughness,double ior,double gloss) {
    std::array<Vec,33> result;
    const Vec colors{linear(r),linear(g),linear(b)};
    const Surface shader(roughness,ior,gloss);
    const double norm=std::sqrt(.36*.36+.44*.44+.82*.82);
    const double lx=-.36/norm, ly=.44/norm, lz=.82/norm;
    const double hn=std::sqrt(lx*lx+ly*ly+(lz+1)*(lz+1));
    for(int i=0;i<33;++i) {
        double t=-1+2.*i/32, nz=std::sqrt(std::max(0.,1-t*t)), nx=normal_x*t, ny=-normal_y*t;
        auto terms=shader(nx*lx+ny*ly+nz*lz,nz,nx*(lx/hn)+ny*(ly/hn)+nz*((lz+1)/hn));
        for(int c=0;c<3;++c) result[i][c]=srgb(colors[c]*terms[0]+terms[1]);
    }
    return result;
}
}
