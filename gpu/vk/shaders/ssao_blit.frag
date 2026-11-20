#version 450
// (OcaDim, Ray-Tracing TEST) Le dernier pas des effets d'ecran (SSAO, SSR) : l'image temporaire est dessinee dans la
// cible du jeu, par un rendu. Une copie ne conviendrait pas : les cibles de rendu du jeu n'ont pas TRANSFER_DST.
// L'alpha est celui que la passe a laisse dans l'image temporaire.
layout(location = 0) in vec2 uv;
layout(location = 0) out vec4 out_color;
layout(binding = 0) uniform sampler2D src;

void main() { out_color = textureLod(src, uv, 0.0); }
