// Isolated evaluation kernel; not loaded by the application.
// Build example (MinGW): g++ -O3 -shared -static-libgcc -static-libstdc++
//   scripts/native_material_probe.cpp -o output/kernel-assessment/material_probe.dll
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>

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

extern "C" __declspec(dllexport) void sphere_pixels(
    double r,double g,double b,double roughness,double ior,double gloss,std::uint8_t* pixels) {
    const double colors[]={linear(b),linear(g),linear(r)};
    const double alpha=std::max(.002,roughness*roughness), a2=alpha*alpha;
    const double norm=std::sqrt(.36*.36+.44*.44+.82*.82), lz=.82/norm;
    const double hz=(lz+1)/std::sqrt(2+2*lz);
    const double f0=std::pow((ior-1)/(ior+1),2);
    const double f=ior==1 ? 0 : (f0+(1-f0)*std::pow(1-hz,5))*gloss;
    for(int i=0;i<128*128;++i) {
        if(!samples[i].valid) { for(int c=0;c<4;++c) pixels[i*4+c]=0; continue; }
        const auto s=samples[i];
        const double nl=s.nl, nv=std::max(.0001,s.nv), nh=s.nh;
        const double diffuse=.2+.8*nl*(1-f);
        double spec=0;
        if(gloss!=0 && nl>0) {
            const double denom=nh*nh*(a2-1)+1;
            const double d=a2/(3.14159265358979323846*std::max(1e-14,denom*denom));
            const double gv=2*nv/(nv+std::sqrt(a2+(1-a2)*nv*nv));
            const double gl=2*nl/std::max(1e-12,nl+std::sqrt(a2+(1-a2)*nl*nl));
            spec=d*gv*gl*f/(4*nv);
        }
        for(int c=0;c<3;++c) pixels[i*4+c]=static_cast<std::uint8_t>(std::nearbyint(srgb(colors[c]*diffuse+spec)*255));
        pixels[i*4+3]=255;
    }
}
