// Catan Board Parameters
hex_flat_to_flat = 75;
tile_tolerance = 1.5;
led_hole_diameter = 15;
frame_depth = 18;
recess_depth = 3;
ledge_thickness = 3;
ledge_width = 6;

// Wire tunnel parameters
tunnel_width = 12;

// USB channel parameters
usb_channel_width = 14;
usb_channel_height = 12;

// Pi Zero W mounting parameters
pi_hole_spacing_x = 58;
pi_hole_spacing_y = 23;
pi_standoff_diameter = 6;
pi_screw_hole_diameter = 2.5;
pi_standoff_height = 6;

// Derived values
hex_radius = (hex_flat_to_flat + tile_tolerance) / 2 / cos(30);
cavity_radius = hex_radius - ledge_width;
cavity_depth = frame_depth - recess_depth - ledge_thickness;
hex_spacing = hex_flat_to_flat + tile_tolerance + 2;
outer_radius = hex_spacing * 3;

// Cut for a single hex with LED hole
module hex_cut_base() {
    rotate([0, 0, 30]) {
        translate([0, 0, frame_depth - recess_depth])
            cylinder(r = hex_radius, h = recess_depth + 1, $fn = 6);
        translate([0, 0, -1])
            cylinder(r = cavity_radius, h = cavity_depth + 1, $fn = 6);
        translate([0, 0, cavity_depth - 1])
            cylinder(d = led_hole_diameter, h = ledge_thickness + 2, $fn = 32);
    }
}

// Center hex - no LED hole, Pi goes here
module center_hex_cut() {
    rotate([0, 0, 30]) {
        translate([0, 0, frame_depth - recess_depth])
            cylinder(r = hex_radius, h = recess_depth + 1, $fn = 6);
        translate([0, 0, -1])
            cylinder(r = cavity_radius, h = cavity_depth + 1, $fn = 6);
    }
}

// Pi mounting standoff
module pi_standoff() {
    difference() {
        cylinder(d = pi_standoff_diameter, h = pi_standoff_height, $fn = 32);
        translate([0, 0, -1])
            cylinder(d = pi_screw_hole_diameter, h = pi_standoff_height + 2, $fn = 32);
    }
}

module pi_standoffs() {
    for (x = [-pi_hole_spacing_x/2, pi_hole_spacing_x/2]) {
        for (y = [-pi_hole_spacing_y/2, pi_hole_spacing_y/2]) {
            translate([x, y, cavity_depth - pi_standoff_height])
                pi_standoff();
        }
    }
}

// USB channel
module usb_channel() {
    translate([0, -usb_channel_width/2, -1])
        cube([hex_spacing * 3, usb_channel_width, usb_channel_height + 1]);
}

// Tunnel cut between two hexes
module tunnel_cut(from_q, from_r, to_q, to_r) {
    from_x = hex_spacing * (from_q + from_r/2);
    from_y = hex_spacing * from_r * sin(60);
    to_x = hex_spacing * (to_q + to_r/2);
    to_y = hex_spacing * to_r * sin(60);
    mid_x = (from_x + to_x) / 2;
    mid_y = (from_y + to_y) / 2;
    angle = atan2(to_y - from_y, to_x - from_x);
    translate([mid_x, mid_y, -1])
        rotate([0, 0, angle])
        translate([-10, -tunnel_width/2, 0])
            cube([20, tunnel_width, cavity_depth + 1]);
}

module place_hex_cut(q, r) {
    x = hex_spacing * (q + r/2);
    y = hex_spacing * r * sin(60);
    translate([x, y, 0])
        hex_cut_base();
}

// Base plate
module base_plate() {
    rotate([0, 0, 30])
    cylinder(r = outer_radius, h = frame_depth, $fn = 6);
}

// Full board
module full_board() {
    union() {
        difference() {
            base_plate();
            center_hex_cut();
            usb_channel();
            
            // Ring 1
            place_hex_cut(1, 0);
            place_hex_cut(0, 1);
            place_hex_cut(-1, 1);
            place_hex_cut(-1, 0);
            place_hex_cut(0, -1);
            place_hex_cut(1, -1);
            
            // Ring 2
            place_hex_cut(2, 0);
            place_hex_cut(1, 1);
            place_hex_cut(0, 2);
            place_hex_cut(-1, 2);
            place_hex_cut(-2, 2);
            place_hex_cut(-2, 1);
            place_hex_cut(-2, 0);
            place_hex_cut(-1, -1);
            place_hex_cut(0, -2);
            place_hex_cut(1, -2);
            place_hex_cut(2, -2);
            place_hex_cut(2, -1);
            
            // Tunnels - center to ring 1
            tunnel_cut(0, 0, 1, 0);
            tunnel_cut(0, 0, 0, 1);
            tunnel_cut(0, 0, -1, 1);
            tunnel_cut(0, 0, -1, 0);
            tunnel_cut(0, 0, 0, -1);
            tunnel_cut(0, 0, 1, -1);
            
            // Tunnels - ring 1 around
            tunnel_cut(1, 0, 0, 1);
            tunnel_cut(0, 1, -1, 1);
            tunnel_cut(-1, 1, -1, 0);
            tunnel_cut(-1, 0, 0, -1);
            tunnel_cut(0, -1, 1, -1);
            tunnel_cut(1, -1, 1, 0);
            
            // Tunnels - ring 1 to ring 2
            tunnel_cut(1, 0, 2, 0);
            tunnel_cut(1, 0, 2, -1);
            tunnel_cut(0, 1, 1, 1);
            tunnel_cut(0, 1, 0, 2);
            tunnel_cut(-1, 1, -1, 2);
            tunnel_cut(-1, 1, -2, 2);
            tunnel_cut(-1, 0, -2, 1);
            tunnel_cut(-1, 0, -2, 0);
            tunnel_cut(0, -1, -1, -1);
            tunnel_cut(0, -1, 0, -2);
            tunnel_cut(1, -1, 1, -2);
            tunnel_cut(1, -1, 2, -2);
            
            // Tunnels - ring 2 around
            tunnel_cut(2, 0, 1, 1);
            tunnel_cut(1, 1, 0, 2);
            tunnel_cut(0, 2, -1, 2);
            tunnel_cut(-1, 2, -2, 2);
            tunnel_cut(-2, 2, -2, 1);
            tunnel_cut(-2, 1, -2, 0);
            tunnel_cut(-2, 0, -1, -1);
            tunnel_cut(-1, -1, 0, -2);
            tunnel_cut(0, -2, 1, -2);
            tunnel_cut(1, -2, 2, -2);
            tunnel_cut(2, -2, 2, -1);
            tunnel_cut(2, -1, 2, 0);
        }
        pi_standoffs();
    }
}

full_board();