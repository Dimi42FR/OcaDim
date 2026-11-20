#version 450
// (OcaDim, Ray-Tracing TEST) Le triangle plein ecran : trois sommets, aucun tampon, les coordonnees se deduisent de
// gl_VertexIndex. L'UV va de 0 a 1 sur l'ecran pour le fragment qui echantillonne l'image (SSAO, SSR).
// (le viewport de ce blit est en hauteur positive : NDC -1 est le haut de l'ecran, et uv = p y tombe juste. Le jeu, lui,
// dessine avec un viewport retourne : d'ou le 1 - y de la reconstruction dans ssr.comp, pas ici)
layout(location = 0) out vec2 uv;

void main() {
    const vec2 p = vec2(float((gl_VertexIndex << 1) & 2), float(gl_VertexIndex & 2));
    uv = p;
    gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}
