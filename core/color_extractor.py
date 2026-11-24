import io
from PIL import Image
from PySide6.QtGui import QColor

class ColorExtractor:
    @staticmethod
    def extract_palette(image_bytes: bytes, fallback_hex: str = "#1DB954") -> dict:
        """
        Analyzes the album cover image to extract:
        - dominant vibrant color (accent)
        - ambient glow color
        - surface tint
        """
        if not image_bytes:
            col = QColor(fallback_hex)
            return ColorExtractor._build_palette(col)

        try:
            image = Image.open(io.BytesIO(image_bytes))
            image = image.convert("RGB")
            # Resize for fast processing
            image.thumbnail((64, 64), Image.Resampling.LANCZOS)
            
            colors = image.getcolors(maxcolors=4096)
            if not colors:
                return ColorExtractor._build_palette(QColor(fallback_hex))

            # Score colors by saturation and brightness to find vibrant music accents
            best_color = None
            highest_score = -1.0

            for count, (r, g, b) in colors:
                # Calculate saturation & luminance
                max_c = max(r, g, b) / 255.0
                min_c = min(r, g, b) / 255.0
                lum = (max_c + min_c) / 2.0
                
                if max_c == min_c:
                    sat = 0.0
                elif lum < 0.5:
                    sat = (max_c - min_c) / (max_c + min_c)
                else:
                    sat = (max_c - min_c) / (2.0 - max_c - min_c)

                # Discard pure near-black, near-white, or washed-out grays
                if lum < 0.15 or lum > 0.88 or sat < 0.25:
                    continue

                # Score based on saturation, healthy luminance and frequency
                score = (sat * 1.5) + (1.0 - abs(lum - 0.55)) + (count / 1000.0)
                if score > highest_score:
                    highest_score = score
                    best_color = (r, g, b)

            if best_color:
                accent = QColor(best_color[0], best_color[1], best_color[2])
            else:
                # If no vibrant color found, pick average color or fallback
                dominant = max(colors, key=lambda item: item[0])[1]
                accent = QColor(dominant[0], dominant[1], dominant[2])
                if accent.lightness() < 40:
                    accent = accent.lighter(160)

            return ColorExtractor._build_palette(accent)
        except Exception as e:
            print(f"[ColorExtractor] Error analyzing image: {e}")
            return ColorExtractor._build_palette(QColor(fallback_hex))

    @staticmethod
    def _build_palette(accent: QColor) -> dict:
        glow = QColor(accent.red(), accent.green(), accent.blue(), 110)
        ambient_bg = QColor(accent.red(), accent.green(), accent.blue(), 25)
        bright_accent = accent.lighter(115)
        
        return {
            "accent": accent.name(),
            "bright_accent": bright_accent.name(),
            "glow": f"rgba({accent.red()}, {accent.green()}, {accent.blue()}, 0.45)",
            "ambient_bg": f"rgba({accent.red()}, {accent.green()}, {accent.blue()}, 0.12)",
            "qcolor_accent": accent,
            "qcolor_glow": glow
        }

