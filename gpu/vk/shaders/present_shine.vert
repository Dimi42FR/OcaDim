#version 450
// (OcaDim 0.0.6) triangle plein ecran pour l'effet de presentation : uv (0,0) en haut a gauche
layout(location = 0) out vec2 v_uv;
void main() {
    const vec2 p = vec2(float((gl_VertexIndex << 1) & 2), float(gl_VertexIndex & 2));
    gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
    v_uv = p;   // (Vulkan : y = -1 est le HAUT de l ecran, donc uv (0,0) en haut a gauche)
}
