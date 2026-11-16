#pragma once
#include <array>
#include <vector>
#include <cstdint>

namespace crystalx {
using Vec = std::array<double,3>;
using Lattice = std::array<Vec,3>;
struct Rule { int a,b; double low2,high2; };
struct Segment { Vec a,b; int source,target; };
struct SearchResult { std::vector<Segment> segments; std::vector<bool> matched; };

void sphere_pixels(double r,double g,double b,double roughness,double ior,double gloss,std::uint8_t* pixels);
std::array<Vec,33> cylinder_colors(double normal_x,double normal_y,double r,double g,double b,
                                  double roughness,double ior,double gloss);
SearchResult search(const Lattice&,const std::vector<Vec>& wrapped,const std::vector<int>& species,
                    const std::vector<Rule>&,const Vec& margin,double cutoff);
}
