import webcolors

value = -12684359

def int_to_rbg(intger):
    unsigned_val = intger & 0xFFFFFFFF
      # Extract ARGB (0xAARRGGBB)
    A = (unsigned_val >> 24) & 0xFF
    R = (unsigned_val >> 16) & 0xFF
    G = (unsigned_val >> 8) & 0xFF
    B = unsigned_val & 0xFF
    
    return (R,G,B)


def closest_colour(requested_colour):
    """
    Find the named CSS3 color closest to 'requested_colour'.
    requested_colour should be an (r, g, b) tuple.
    """
    min_colours = {}
    for hex_value, color_name in webcolors.CSS3_HEX_TO_NAMES.items():
        r_c, g_c, b_c = webcolors.hex_to_rgb(hex_value)
        # Compute a simple Euclidean distance
        rd = (r_c - requested_colour[0]) ** 2
        gd = (g_c - requested_colour[1]) ** 2
        bd = (b_c - requested_colour[2]) ** 2
        min_colours[rd + gd + bd] = color_name
    return min_colours[min(min_colours.keys())]

def get_colour_name(requested_colour):
    """
    Return the closest CSS3 color name to 'requested_colour'.
    If it is an exact match, return that. Otherwise return the nearest name.
    """
    try:
        # Attempt exact match
        return webcolors.rgb_to_name(requested_colour, spec='css3')
    except ValueError:
        # Fallback: find closest match
        return closest_colour(requested_colour)

# Example usage
rgb = int_to_rbg(value)  # from the -12684359 example
color_name = get_colour_name(rgb)
print("Closest CSS3 color name:", color_name)
