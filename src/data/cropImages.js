// Real crop images from Unsplash (free to use)
// Each crop has a high-quality photo URL

const cropImages = {
  wheat: {
    image: 'https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?w=600&h=400&fit=crop',
    emoji: '🌾',
  },
  rice: {
    image: 'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=600&h=400&fit=crop',
    emoji: '🍚',
  },
  maize: {
    image: 'https://images.unsplash.com/photo-1551754655-cd27e38d2076?w=600&h=400&fit=crop',
    emoji: '🌽',
  },
  corn: {
    image: 'https://images.unsplash.com/photo-1551754655-cd27e38d2076?w=600&h=400&fit=crop',
    emoji: '🌽',
  },
  cotton: {
    image: 'https://images.unsplash.com/photo-1605000797499-95a51c5269ae?w=600&h=400&fit=crop',
    emoji: '☁️',
  },
  sugarcane: {
    image: 'https://images.unsplash.com/photo-1619566636858-adf3ef46400b?w=600&h=400&fit=crop',
    emoji: '🎋',
  },
  soybean: {
    image: 'https://images.unsplash.com/photo-1599420186946-7b6fb4e287f3?w=600&h=400&fit=crop',
    emoji: '🫘',
  },
  potato: {
    image: 'https://images.unsplash.com/photo-1518977676601-b53f82ber40?w=600&h=400&fit=crop',
    emoji: '🥔',
  },
  tomato: {
    image: 'https://images.unsplash.com/photo-1546470427-0d4db154ceb8?w=600&h=400&fit=crop',
    emoji: '🍅',
  },
  onion: {
    image: 'https://images.unsplash.com/photo-1618512496248-a07fe83aa8cb?w=600&h=400&fit=crop',
    emoji: '🧅',
  },
  groundnut: {
    image: 'https://images.unsplash.com/photo-1567306226416-28f0efdc88ce?w=600&h=400&fit=crop',
    emoji: '🥜',
  },
  moong: {
    image: 'https://images.unsplash.com/photo-1596591868231-05e882a39b1f?w=600&h=400&fit=crop',
    emoji: '🫘',
  },
  mustard: {
    image: 'https://images.unsplash.com/photo-1599909533601-aa643a9a4a36?w=600&h=400&fit=crop',
    emoji: '🌻',
  },
  chickpea: {
    image: 'https://images.unsplash.com/photo-1515543237350-b3eea1ec8082?w=600&h=400&fit=crop',
    emoji: '🫘',
  },
  mango: {
    image: 'https://images.unsplash.com/photo-1553279768-865429fa0078?w=600&h=400&fit=crop',
    emoji: '🥭',
  },
  banana: {
    image: 'https://images.unsplash.com/photo-1528825871115-3581a5387919?w=600&h=400&fit=crop',
    emoji: '🍌',
  },
  chilli: {
    image: 'https://images.unsplash.com/photo-1583119022894-919a68a3d0e3?w=600&h=400&fit=crop',
    emoji: '🌶️',
  },
  spinach: {
    image: 'https://images.unsplash.com/photo-1576045057995-568f588f82fb?w=600&h=400&fit=crop',
    emoji: '🥬',
  },
  tea: {
    image: 'https://images.unsplash.com/photo-1556679343-c7306c1976bc?w=600&h=400&fit=crop',
    emoji: '🍵',
  },
  coffee: {
    image: 'https://images.unsplash.com/photo-1447933601403-0c6688de566e?w=600&h=400&fit=crop',
    emoji: '☕',
  },
}

// Default image for unknown crops
const defaultCropImage = {
  image: 'https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?w=600&h=400&fit=crop',
  emoji: '🥦',
}

export function getCropImage(cropName) {
  if (!cropName) return defaultCropImage
  const key = cropName.toLowerCase().trim()
  return cropImages[key] || defaultCropImage
}

export function getCropImageUrl(cropName) {
  return getCropImage(cropName).image
}

export function getCropEmoji(cropName) {
  return getCropImage(cropName).emoji
}

export default cropImages
