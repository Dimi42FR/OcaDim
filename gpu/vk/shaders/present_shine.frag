#version 450
// (OcaDim 0.0.6) « Rue mouillee », applique a la PRESENTATION, sur l'image finale de la fenetre (format d'ecran, 8 bits).
//
// Pourquoi ici : le tampon de rendu du jeu est en B10G11R11 (flottant compacte), et ce pilote l'ecrit mal depuis notre code
// (blit de conversion : bruit ; passe de rendu : assombrissement ; storage : canaux inverses). A la presentation l'image
// est deja convertie dans le format de l'ecran : l'ecriture y est celle d'ImGui, donc fiable.
//
// L'effet ne lit ni normale ni profondeur : la rue est en bas de l'image. Une chaussee mouillee s'assombrit, prend une
// lueur de ciel rasante, et scintille un peu. Rien ne peut baver sur les facades ni dependre du hors-champ.
layout(binding = 0) uniform sampler2D pic;

layout(push_constant) uniform P {
    vec4 uv;         // (echelle x, echelle y, decalage x, decalage y) : la zone de l'image source a lire
    float strength;  // (0 = aucun effet, 1 = plein)
    float time;      // (secondes, pour les scintillements)
    vec2 pad;
} pc;

layout(location = 0) in vec2 v_uv;
layout(location = 0) out vec4 out_col;

float hash21(vec2 p) {
    p = fract(p * vec2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
}

vec3 src(vec2 uv) { return texture(pic, pc.uv.zw + uv * pc.uv.xy).rgb; }

void main() {
    const vec3 c = src(v_uv);
    const float y = v_uv.y;   // (0 en haut de l'ecran)

    // (la rue : le bas de l'image ; la ou elle s'eloigne (vers l'horizon) est le plus mouille, le tout premier plan reste
    // plus mat - comme une vraie chaussee)
    const float road = smoothstep(0.38, 0.66, y) * mix(1.0, 0.55, smoothstep(0.82, 1.0, y));
    const float band = smoothstep(0.42, 0.62, y) * (1.0 - smoothstep(0.62, 0.86, y));
    const float s = pc.strength * road;

    // (le ciel, ecrete : l'image de presentation peut encore porter des valeurs au-dessus de 1)
    const vec3 sky = min(src(vec2(0.5, 0.02)), vec3(1.5));
    const vec3 sky_grey = mix(vec3(dot(sky, vec3(0.2126, 0.7152, 0.0722))), sky, 0.55);

    // (1) la pierre humide s'assombrit
    vec3 col = c * (1.0 - 0.22 * s);
    // (2) la lueur de ciel, rasante : c'est elle qui fait « mouille »
    col = mix(col, sky_grey, clamp(0.16 * s * (0.35 + 0.65 * band), 0.0, 0.6));
    // (3) quelques scintillements, uniquement sur la rue, petits et rares
    const vec2 gp = gl_FragCoord.xy / 2.5;
    float spark = 0.0;
    for (int k = 0; k < 3; k++) {
        const float ph = hash21(floor(gp) + float(k) * 17.0);
        const float life = fract(pc.time * (0.35 + 0.55 * ph) + ph);
        const float on = smoothstep(0.84, 0.89, life) * (1.0 - smoothstep(0.93, 0.99, life));
        const float spot = step(0.960, hash21(floor(gp) + 3.7 + float(k) * 5.1));
        spark += on * spot;
    }
    col += sky_grey * clamp(spark, 0.0, 1.0) * pc.strength * road * 0.35;

    out_col = vec4(col, 1.0);
}
