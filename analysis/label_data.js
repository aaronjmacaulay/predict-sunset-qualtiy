// label_data.js — hand-tagged label dataset for the sunset rating labels analysis.
//
// Source text: user-input/photo-ratings.md (8 photos x 2 raters = 16 reviews).
// Each review was read and scored per label on a signed scale:
//   +1 = theme was praised   -1 = theme was criticized   0 = not mentioned (or a wash)
//
// Labels are grouped into three tiers (see analysis/README.md for the reasoning):
//   sky_weather     - forecastable from a weather model (cloud cover, type/structure, color, aerosol clarity)
//   geometry        - forecastable from sun position + viewpoint, no weather model needed
//   photo_specific  - an artifact of that exact photo/photographer/location; not forecastable

const LABELS = [
  { name: "cloud_amount", tier: "sky_weather" },
  { name: "cloud_type", tier: "sky_weather" },
  { name: "sun_blocking_clouds", tier: "sky_weather" },
  { name: "color_vibrancy", tier: "sky_weather" },
  { name: "gradient_transition", tier: "sky_weather" },
  { name: "cloud_reflection", tier: "sky_weather" },
  { name: "sun_timing", tier: "geometry" },
  { name: "water_reflection", tier: "geometry" },
  { name: "foreground_quality", tier: "photo_specific" },
  { name: "focus_sharpness", tier: "photo_specific" },
  { name: "obstructions", tier: "photo_specific" },
  { name: "sun_obstruction_by_foreground", tier: "photo_specific" },
  { name: "authenticity", tier: "photo_specific" },
];

const ROWS = [
  { photo: "IMG_0430.JPG", rater: "Sandy", score: 4, labels: { cloud_amount: 1, cloud_type: 1, sun_blocking_clouds: 0, color_vibrancy: 1, gradient_transition: 0, cloud_reflection: -1, sun_timing: 0, water_reflection: 0, foreground_quality: -1, focus_sharpness: -1, obstructions: 0, sun_obstruction_by_foreground: 0, authenticity: 0 } },
  { photo: "IMG_0430.JPG", rater: "Aaron", score: 7, labels: { cloud_amount: 1, cloud_type: -1, sun_blocking_clouds: 0, color_vibrancy: 1, gradient_transition: 0, cloud_reflection: 0, sun_timing: 0, water_reflection: 0, foreground_quality: 0, focus_sharpness: 0, obstructions: 0, sun_obstruction_by_foreground: 0, authenticity: 0 } },

  { photo: "IMG_0914.jpg", rater: "Sandy", score: 3, labels: { cloud_amount: 0, cloud_type: 0, sun_blocking_clouds: 0, color_vibrancy: 0, gradient_transition: 0, cloud_reflection: 0, sun_timing: 0, water_reflection: 0, foreground_quality: -1, focus_sharpness: -1, obstructions: 0, sun_obstruction_by_foreground: 0, authenticity: 0 } },
  { photo: "IMG_0914.jpg", rater: "Aaron", score: 5, labels: { cloud_amount: 0, cloud_type: 1, sun_blocking_clouds: 0, color_vibrancy: -1, gradient_transition: 0, cloud_reflection: 1, sun_timing: 0, water_reflection: 0, foreground_quality: 0, focus_sharpness: 0, obstructions: 0, sun_obstruction_by_foreground: 0, authenticity: 0 } },

  { photo: "IMG_2081.jpg", rater: "Sandy", score: 6, labels: { cloud_amount: 0, cloud_type: 1, sun_blocking_clouds: 0, color_vibrancy: 1, gradient_transition: 1, cloud_reflection: 0, sun_timing: 0, water_reflection: 0, foreground_quality: 1, focus_sharpness: -1, obstructions: -1, sun_obstruction_by_foreground: 0, authenticity: 0 } },
  { photo: "IMG_2081.jpg", rater: "Aaron", score: 8, labels: { cloud_amount: 1, cloud_type: 0, sun_blocking_clouds: 0, color_vibrancy: 1, gradient_transition: -1, cloud_reflection: 1, sun_timing: 0, water_reflection: 0, foreground_quality: 0, focus_sharpness: 0, obstructions: 0, sun_obstruction_by_foreground: 0, authenticity: 0 } },

  { photo: "IMG_3231.jpg", rater: "Sandy", score: 3, labels: { cloud_amount: -1, cloud_type: 0, sun_blocking_clouds: 0, color_vibrancy: 1, gradient_transition: 0, cloud_reflection: 0, sun_timing: 1, water_reflection: 0, foreground_quality: -1, focus_sharpness: -1, obstructions: -1, sun_obstruction_by_foreground: 0, authenticity: 0 } },
  { photo: "IMG_3231.jpg", rater: "Aaron", score: 5, labels: { cloud_amount: 0, cloud_type: 0, sun_blocking_clouds: 0, color_vibrancy: -1, gradient_transition: 1, cloud_reflection: 0, sun_timing: 0, water_reflection: 0, foreground_quality: 0, focus_sharpness: 0, obstructions: 0, sun_obstruction_by_foreground: 0, authenticity: 0 } },

  { photo: "IMG_3698.jpg", rater: "Sandy", score: 7, labels: { cloud_amount: 0, cloud_type: 1, sun_blocking_clouds: 0, color_vibrancy: 0, gradient_transition: 0, cloud_reflection: 0, sun_timing: 0, water_reflection: 0, foreground_quality: 0, focus_sharpness: 0, obstructions: 0, sun_obstruction_by_foreground: 0, authenticity: 0 } },
  { photo: "IMG_3698.jpg", rater: "Aaron", score: 6, labels: { cloud_amount: 1, cloud_type: -1, sun_blocking_clouds: 0, color_vibrancy: 1, gradient_transition: 0, cloud_reflection: 0, sun_timing: -1, water_reflection: -1, foreground_quality: 1, focus_sharpness: 0, obstructions: 0, sun_obstruction_by_foreground: 0, authenticity: 0 } },

  { photo: "IMG_3711.jpg", rater: "Sandy", score: 8, labels: { cloud_amount: 0, cloud_type: 0, sun_blocking_clouds: 0, color_vibrancy: 0, gradient_transition: 0, cloud_reflection: 1, sun_timing: 0, water_reflection: 0, foreground_quality: 0, focus_sharpness: 0, obstructions: 0, sun_obstruction_by_foreground: 1, authenticity: 0 } },
  { photo: "IMG_3711.jpg", rater: "Aaron", score: 8, labels: { cloud_amount: -1, cloud_type: 0, sun_blocking_clouds: 0, color_vibrancy: 1, gradient_transition: 0, cloud_reflection: 0, sun_timing: -1, water_reflection: 0, foreground_quality: 1, focus_sharpness: 0, obstructions: -1, sun_obstruction_by_foreground: 1, authenticity: 0 } },

  { photo: "IMG_7206.jpg", rater: "Sandy", score: 6, labels: { cloud_amount: 0, cloud_type: 0, sun_blocking_clouds: 0, color_vibrancy: 1, gradient_transition: 0, cloud_reflection: 0, sun_timing: 0, water_reflection: 0, foreground_quality: 0, focus_sharpness: 0, obstructions: -1, sun_obstruction_by_foreground: 0, authenticity: 0 } },
  { photo: "IMG_7206.jpg", rater: "Aaron", score: 7, labels: { cloud_amount: -1, cloud_type: 1, sun_blocking_clouds: 0, color_vibrancy: 1, gradient_transition: 0, cloud_reflection: 1, sun_timing: 0, water_reflection: 0, foreground_quality: 0, focus_sharpness: 0, obstructions: 0, sun_obstruction_by_foreground: 0, authenticity: 0 } },

  { photo: "IMG_7230.jpg", rater: "Sandy", score: 6, labels: { cloud_amount: -1, cloud_type: 0, sun_blocking_clouds: 0, color_vibrancy: 1, gradient_transition: 1, cloud_reflection: 0, sun_timing: 0, water_reflection: 1, foreground_quality: 0, focus_sharpness: 0, obstructions: -1, sun_obstruction_by_foreground: 0, authenticity: 0 } },
  { photo: "IMG_7230.jpg", rater: "Aaron", score: 3, labels: { cloud_amount: -1, cloud_type: 0, sun_blocking_clouds: 0, color_vibrancy: 1, gradient_transition: 0, cloud_reflection: 0, sun_timing: 0, water_reflection: -1, foreground_quality: 0, focus_sharpness: 0, obstructions: 0, sun_obstruction_by_foreground: 0, authenticity: 0 } },
];

module.exports = { LABELS, ROWS };
