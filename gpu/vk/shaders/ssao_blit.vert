#version 450
// (OcaDim, Ray-Tracing TEST) Le triangle plein ecran : trois sommets, aucun tampon, les coordonnees se deduisent de
// gl_VertexIndex. L'UV va de 0 a 1 sur l'ecran pour le fragment qui echantillonne l'image (SSAO, SSR).
// (l'axe y de l'ecran va vers le bas, celui du NDC vers le haut : d'ou le 1 - y, sinon l'image est retournee)
layout(location = 0) out vec2 uv;

void main() {
    const vec2 p = vec2(float((gl_VertexIndex << 1) & 2), float(gl_VertexIndex & 2));
    uv = vec2(p.x, 1.0 - p.y);
    gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}
