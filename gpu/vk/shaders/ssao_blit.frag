#version 450
// (OcaDim, Ray-Tracing TEST) Le dernier pas du SSAO : l'image temporaire (couleur x facteur d'occlusion) est dessinee
// dans la cible du jeu, par un rendu. Une copie ne conviendrait pas : les cibles de rendu du jeu n'ont pas TRANSFER_DST.
layout(location = 0) in vec2 uv;
layout(location = 0) out vec4 out_color;
layout(binding = 0) uniform sampler2D src;

void main() { out_color = vec4(textureLod(src, uv, 0.0).rgb, 1.0); }
