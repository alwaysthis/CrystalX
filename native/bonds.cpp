#include "kernels.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <map>
#include <stdexcept>
#include <unordered_map>

namespace crystalx {
namespace {
using Bin=std::array<int,3>;
struct Hash {
    std::size_t operator()(const Bin& key) const {
        std::size_t h=0;
        for(int v:key) h^=std::hash<int>{}(v)+0x9e3779b9+(h<<6)+(h>>2);
        return h;
    }
};
struct Image { Vec frac,point; int source; Bin bin; };
Vec cartesian(const Vec& f,const Lattice& lattice) {
    Vec result{};
    for(int j=0;j<3;++j) for(int i=0;i<3;++i) result[j]+=f[i]*lattice[i][j];
    return result;
}
int integer(double value) {
    // Reserve one slot on each end for the neighboring-bin offset.
    if(!std::isfinite(value) || value<=std::numeric_limits<int>::min() || value>=std::numeric_limits<int>::max())
        throw std::overflow_error("Periodic search bounds exceed integer range");
    return static_cast<int>(value);
}
bool clip(const Vec& a,const Vec& b,Vec& ca,Vec& cb) {
    double low=0, high=1;
    for(int k=0;k<3;++k) {
        double d=b[k]-a[k];
        if(std::abs(d)<1e-12) { if(a[k]<-1e-9 || a[k]>1+1e-9) return false; }
        else {
            double u=-a[k]/d, v=(1-a[k])/d;
            if(u>v) std::swap(u,v);
            low=std::max(low,u); high=std::min(high,v);
            if(high-low<1e-9) return false;
        }
    }
    for(int k=0;k<3;++k) { ca[k]=a[k]+low*(b[k]-a[k]); cb[k]=a[k]+high*(b[k]-a[k]); }
    return true;
}
}

SearchResult search(const Lattice& lattice,const std::vector<Vec>& wrapped,const std::vector<int>& species,
                    const std::vector<Rule>& rules,const Vec& margin,double cutoff) {
    SearchResult result; result.matched.resize(rules.size(),false);
    std::map<std::pair<int,int>,std::vector<std::size_t>> pairs;
    for(std::size_t i=0;i<rules.size();++i) pairs[std::minmax(rules[i].a,rules[i].b)].push_back(i);
    std::vector<Image> images;
    std::unordered_map<Bin,std::vector<std::size_t>,Hash> bins;
    for(std::size_t source=0;source<wrapped.size();++source) {
        const Vec f=wrapped[source]; Bin low,high;
        for(int k=0;k<3;++k) {
            low[k]=integer(std::ceil(-margin[k]-f[k]-1e-9));
            high[k]=integer(std::floor(1+margin[k]-f[k]+1e-9));
        }
        for(int x=low[0];x<=high[0];++x) for(int y=low[1];y<=high[1];++y) for(int z=low[2];z<=high[2];++z) {
            Vec frac{f[0]+x,f[1]+y,f[2]+z}; Vec point=cartesian(frac,lattice); Bin bin;
            for(int k=0;k<3;++k) bin[k]=integer(std::floor(point[k]/cutoff));
            bins[bin].push_back(images.size()); images.push_back({frac,point,static_cast<int>(source),bin});
        }
    }
    for(std::size_t i=0;i<images.size();++i) {
        const auto& a=images[i];
        for(int x=-1;x<=1;++x) for(int y=-1;y<=1;++y) for(int z=-1;z<=1;++z) {
            Bin bin{a.bin[0]+x,a.bin[1]+y,a.bin[2]+z}; auto found=bins.find(bin);
            if(found==bins.end()) continue;
            for(auto j:found->second) {
                if(j<=i) continue;
                const auto& b=images[j]; auto pair=pairs.find(std::minmax(species[a.source],species[b.source]));
                if(pair==pairs.end()) continue;
                double distance=0;
                for(int k=0;k<3;++k) { double d=a.point[k]-b.point[k]; distance+=d*d; }
                if(distance<1e-16) continue;
                auto matches=[&](std::size_t index) { const auto& rule=rules[index]; return rule.low2-1e-12<=distance && distance<=rule.high2+1e-12; };
                if(!std::any_of(pair->second.begin(),pair->second.end(),matches)) continue;
                Vec ca,cb; if(!clip(a.frac,b.frac,ca,cb)) continue;
                for(auto index:pair->second) if(matches(index)) result.matched[index]=true;
                // Python retains its exact round(v,8), geometric dedup and output ordering.
                result.segments.push_back({ca,cb,a.source,b.source});
            }
        }
    }
    return result;
}
}
