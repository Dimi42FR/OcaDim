LE STEP 3 — LE PREFETCH DES DESCRIPTEURS (le design, mappé au code)
====================================================================

== POURQUOI C'EST LE MEILLEUR PARI (validé par nos mesures) ==
Le replay lourd: 8,7 ms — dont draw ~9-14 (les workers parallèles inclus),
descriptors 2,5-4,3, commands 3,5-5,9. L'offload des descriptors+commands
fait descendre le thread de replay vers ~5-6 ms -> les fps montent dans
NOTRE config validée (parallel 4/32, zéro flash — pas d'async impliqué!).

== L'ARCHITECTURE (mappée aux lignes) ==
Le dry pass (vk_replay.cpp:1935-1946) tourne DÉJÀ avant les segments dans
notre config — il connaît les draws à venir et leurs états (les ParPoints
portent le NvnState ✓).

1. LE DRY PASS FILE LES DRAWS: à chaque draw du dry pass (op_is_work),
   au lieu de seulement marquer le point: empiler {l'état au point (le
   ParPoint ✓), la position du stream} dans une queue de prefetch.

2. LE THREAD DE PREFETCH (1-2 helpers): pour chaque draw empilé:
   - la résolution des textures: texture_view_of (vk_draw.cpp:3965) —
     les handles lus via memory_read_as_submitted = LA CAPTURE ✓ stable
     (les bytes au submit — les mêmes que la record lira ✓);
   - la construction du payload des writes (out.imgs, les samplers,
     les offsets — le données de build_descriptors:3323-4014);
   - le fingerprint (desc_fp ✓) calculé et stocké avec le payload.
   Le tout dans une arène par draw (le pattern Taken de NX2navi ✓).

3. LE REPLAY THREAD CONSOMME: à build_descriptors du draw (le record):
   - le lookup du payload pré-construit (par la position du stream/le
     fingerprint) sous le lock du prefetch;
   - la vérification: les versions (desc_fp ✓) + la capture vue
     (cap_view_bump ✓) — si identiques: memcpy du payload (léger) au
     lieu du build complet (la résolution + les tables);
   - si différent (le jeu a réécrit une table entre-temps): le fallback
     = le build local comme aujourd'hui ✓ (la correction garantie).

4. LES GARDE-FOUS:
   - le fingerprint à la consommation est LE garde-fou de justesse ✓
     (le même mécanisme que la réutilisation du voisin — éprouvé);
   - les payloads: une arène bornée (les draws du buffer courant —
     ~100-500 draws, quelques Mo) — la pression = la backpressure sur
     la queue du prefetch;
   - les textures évincées entre le prefetch et le record: la vérif
     texture_view_of au consommé (la vue par handle ✓).

== LES PIÈCES (l'ordre d'implémentation, chacune testable) ==
P1. La queue du prefetch + le thread (le squelette, off par défaut
    RX_VK_DESC_PREFETCH=1) — le dry pass empile, le thread consomme et
    JETTE (le plomberie seule, mesurable: les stats de la queue).
P2. La construction du payload dans le thread (la résolution copiée de
    build_descriptors — la partie pure: les handles->les vues->les
    imgs; les garde-fous de justesse à la consommation).
P3. La consommation au record (le memcpy du payload + le fallback).
P4. Les commands: le même pattern pour la partie cmds (les hazards/
    barriers pré-calculés) — APRÈS que P1-P3 tiennent.

== P2 — LE CONTRAT AU NIVEAU DU CODE (la session copie ceci) ==
struct PfPayload {                       // (par draw, dans l'arène du helper)
    size_t stream_pos;                   // (l'offset du draw dans le segment — la clé)
    uint64_t prog_key;                   // (la vérif: le programme attendu)
    std::vector<{sampler, view, layout}> imgs;   // (la résolution copiée: 4014)
    std::vector<uint8_t> ub_bytes;       // (les données ub_overlay résolues)
    // + le fingerprint desc_fp copié (la vérif à la consommation)
};
LE HELPER (par ParPoint drainé): re-walk le segment (de pt.p à la borne
  suivante) en reproduisant l'évolution d'état du dry pass (le MÊME ordre
  des ops — la contrainte dure: toute divergence = les mauvaises vues), et
  pour chaque draw: la résolution textures (texture_view_of:3965 + les
  tables via memory_read_as_submitted = la capture ✓ stable) + les ub
  overlays (ub_overlay:1083, la base depuis la capture ✓) — le payload
  stocké dans l'arène, la queue à la liste des payloads finis.
LE CONSOMMÉ (build_descriptors, au record du draw — le même stream_pos):
  le lookup du payload fini (sous le lock du prefetch) + la VÉRIF: le
  fingerprint (desc_fp ✓) + la capture vue (cap_view_bump ✓) + le prog
  key — identiques: memcpy du payload (les imgs + les ub bytes) dans le
  stream (le stream_alloc reste sur le record ✓ l'ordre préservé);
  différent: le build local complet (le fallback ✓ la justesse garantie).
LE HELPER: BELOW_NORMAL ✓ (le pattern de priorité validé), l'arène bornée
  au buffer courant (la backpressure sur la queue), 1-2 helpers.
LE TEST: les stats (les payloads servis/le fallback) dans la ligne de
  frame + la route lourde -> les fps + le replay.


== LES RISQUES ET LES PARADES ==
- La justesse: le fingerprint + la vue à la consommation (le même
  mécanisme que desc_fp — éprouvé).
- La contention: les helpers BELOW_NORMAL (le patch de priorité ✓ —
  le pattern validé: les cœurs rendus au jeu au besoin).
- La mémoire: les arènes bornées par buffer courant ✓.
- Le fallback: toujours disponible (le build local au consommé) — le
  pire cas = le comportement actuel.

== L'HONNÊTETÉ ==
C'est un chantier de ~2-3 h soignées (P1-P3) + le test flash/fps. Les
pièces P1-P2 sont mécaniques (le squelette + la résolution copiée);
P3 est la sensibilité (le consommé doit matcher exactement le record);
P4 est le bonus. Le design ci-dessus est le contrat — chaque pièce
vérifiable indépendamment, le daily driver jamais en danger.
