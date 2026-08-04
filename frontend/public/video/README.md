# Vidéos d'ambiance (facultatives)

Le hero de la page d'accueil utilise actuellement la photo
`public/img/landing-hero-field.jpg` via `<HeroMedia>`.

Pour réactiver une vidéo plus tard, déposez un MP4 ici :

```
public/video/hero-field.mp4
```

puis passez `videoSrc="/video/hero-field.mp4"` à `<HeroMedia>` dans
`src/routes/index.tsx`.

Recommandations : MP4 H.264, ~1280×720, < 3 Mo, sans audio, en boucle.
