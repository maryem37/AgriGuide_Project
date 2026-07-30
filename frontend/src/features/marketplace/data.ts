export type Listing = {
  id: string;
  kind: "recolte" | "dechet";
  title: string;
  crop: string;
  quantity: string;
  price: string;
  freePrice?: boolean;
  region: string;
  distance: string;
  emoji: string;
  description: string;
  utility?: string;
  contact: { phone: string; email: string };
  status?: "disponible" | "reserve" | "expire";
  mine?: boolean;
};

export const listings: Listing[] = [
  {
    id: "1",
    kind: "recolte",
    title: "Blé tendre bio",
    crop: "Blé",
    quantity: "3,5 tonnes",
    price: "285 €/t",
    region: "Eure-et-Loir",
    distance: "12 km",
    emoji: "🌾",
    description: "Récolte 2026, blé tendre bio certifié AB. Taux de protéines 11,8%. Livraison possible dans un rayon de 40 km.",
    contact: { phone: "06 12 34 56 78", email: "jean.martin@fermedespres.fr" },
    status: "disponible",
    mine: true,
  },
  {
    id: "2",
    kind: "dechet",
    title: "Paille de blé",
    crop: "Paille",
    quantity: "200 bottes",
    price: "À convenir",
    freePrice: true,
    region: "Loiret",
    distance: "23 km",
    emoji: "🌿",
    description: "Bottes rondes de paille de blé, bon état, stockées à l'abri.",
    utility: "Idéale pour la litière animale, le paillage de sol ou l'isolation naturelle.",
    contact: { phone: "07 88 22 44 11", email: "contact@fermedelabatie.fr" },
    status: "disponible",
    mine: true,
  },
  {
    id: "3",
    kind: "recolte",
    title: "Colza HOLL",
    crop: "Colza",
    quantity: "8 tonnes",
    price: "460 €/t",
    region: "Yvelines",
    distance: "34 km",
    emoji: "🌼",
    description: "Colza HOLL, débouché huile alimentaire. Livraison assurée.",
    contact: { phone: "06 55 44 33 22", email: "amelie@grangehaut.fr" },
    status: "disponible",
  },
  {
    id: "4",
    kind: "dechet",
    title: "Marc de raisin",
    crop: "Vigne",
    quantity: "1,2 tonnes",
    price: "Gratuit",
    freePrice: true,
    region: "Loir-et-Cher",
    distance: "58 km",
    emoji: "🍇",
    description: "Marc de raisin issu des vendanges 2026, à récupérer sur place.",
    utility: "Compostage, méthanisation, ou distillation artisanale.",
    contact: { phone: "06 77 88 99 00", email: "domaine@coteauxsud.fr" },
    status: "disponible",
  },
  {
    id: "5",
    kind: "recolte",
    title: "Tournesol",
    crop: "Tournesol",
    quantity: "5 tonnes",
    price: "410 €/t",
    region: "Indre-et-Loire",
    distance: "72 km",
    emoji: "🌻",
    description: "Récolte propre, taux d'huile 43%. Prêt à charger.",
    contact: { phone: "06 11 22 33 44", email: "pierre.laurent@agri.fr" },
    status: "reserve",
    mine: true,
  },
  {
    id: "6",
    kind: "dechet",
    title: "Fumier de bovins",
    crop: "Fumier",
    quantity: "15 m³",
    price: "20 €/m³",
    region: "Eure-et-Loir",
    distance: "8 km",
    emoji: "🐄",
    description: "Fumier bien décomposé, prêt à épandre.",
    utility: "Amendement organique riche en azote, potassium et phosphore.",
    contact: { phone: "06 45 67 89 10", email: "elevage.dupre@gmail.com" },
    status: "disponible",
  },
];
