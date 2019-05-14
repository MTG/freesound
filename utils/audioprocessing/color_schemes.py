from PIL import Image, ImageDraw, ImageColor
from functools import partial


def desaturate(rgb, amount):
    """
        desaturate colors by amount
        amount == 0, no change
        amount == 1, grey
    """
    luminosity = sum(rgb) / 3.0
    desat = lambda color: color - amount * (color - luminosity)

    return tuple(map(int, map(desat, rgb)))


def color_from_value(value):
    """ given a value between 0 and 1, return an (r,g,b) tuple """
    return ImageColor.getrgb("hsl(%d,%d%%,%d%%)" % (int((1.0 - value) * 360), 80, 50))


FREESOUND2_COLOR_SCHEME = 'Freesound2'
BEASTWHOOSH_COLOR_SCHEME = 'FreesoundBeastWhoosh'
CYBERPUNK_COLOR_SCHEME = 'Cyberpunk'
RAINFOREST_COLOR_SCHEME = 'Rainforest'
DEFAULT_COLOR_SCHEME_KEY = FREESOUND2_COLOR_SCHEME


COLOR_SCHEMES = {
    FREESOUND2_COLOR_SCHEME: {
        'wave_colors': [
            (0, 0, 0),  # Background color
            (50, 0, 200),  # Low spectral cetroid
            (0, 220, 80),
            (255, 224, 0),
            (255, 70, 0),  # High spectral cetroid
        ],
        'spec_colors': [
            (0, 0, 0),  # Background color
            (58/4, 68/4, 65/4),
            (80/2, 100/2, 153/2),
            (90, 180, 100),
            (224, 224, 44),
            (255, 60, 30),
            (255, 255, 255)
         ]
    },
    BEASTWHOOSH_COLOR_SCHEME: {
        'wave_colors': [
            (255, 255, 255),  # Background color
            (29, 159, 181),  # 1D9FB5, Low spectral cetroid
            (28, 174, 72),  # 1CAE48
            (255, 158, 53),  # FF9E35
            (255, 53, 70),  # FF3546, High spectral cetroid
        ],
        'spec_colors': [
            (0, 0, 0),  # Background color/Low spectral energy
            (29, 159, 181),  # 1D9FB5
            (28, 174, 72),  # 1CAE48
            (255, 158, 53),  # FF9E35
            (255, 53, 70),  # FF3546, High spectral energy
         ]
    },
    CYBERPUNK_COLOR_SCHEME: {
        'wave_colors': [(0, 0, 0)] + [color_from_value(value/29.0) for value in range(0, 30)],
        'spec_colors': [(0, 0, 0)] + [color_from_value(value/29.0) for value in range(0, 30)],
    },
    RAINFOREST_COLOR_SCHEME: {
        'wave_colors': [(213, 217, 221)] + map(partial(desaturate, amount=0.7), [
                        (50, 0, 200),
                        (0, 220, 80),
                        (255, 224, 0),
                     ]),
        'spec_colors': [(213, 217, 221)] + map(partial(desaturate, amount=0.7), [
                        (50, 0, 200),
                        (0, 220, 80),
                        (255, 224, 0),
                     ]),
    }
}
