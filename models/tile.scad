// Catan Hex Tile
// Designed for sticker top and translucent number token

// Tile parameters - should match frame recess
tile_flat_to_flat = 75;
tile_thickness = 3;

// Light hole parameters
light_hole_diameter = 15;

// Token recess parameters
token_diameter = 30;
token_recess_depth = 2;

// Derived values
tile_radius = tile_flat_to_flat / 2 / cos(30);

module hex_tile() {
    difference() {
        // Main hex body
        rotate([0, 0, 30])
            cylinder(r = tile_radius, h = tile_thickness, $fn = 6);
        
        // Light hole through center
        translate([0, 0, -1])
            cylinder(d = light_hole_diameter, h = tile_thickness + 2, $fn = 32);
        
        // Token recess on top
        translate([0, 0, tile_thickness - token_recess_depth])
            cylinder(d = token_diameter, h = token_recess_depth + 1, $fn = 64);
    }
}

hex_tile();
