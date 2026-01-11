// Catan Number Tokens - All tokens for a standard game
// Print in clear/translucent PLA
// Standard set: 2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12

// Token parameters
token_diameter = 29.5;
token_thickness = 2;
number_height = 1.2;  // How high the number is raised
number_size = 14;

// Layout
spacing = 35;

// Probability dots
function get_dots(n) = 
    (n == 2 || n == 12) ? 1 :
    (n == 3 || n == 11) ? 2 :
    (n == 4 || n == 10) ? 3 :
    (n == 5 || n == 9) ? 4 :
    (n == 6 || n == 8) ? 5 : 0;

dot_diameter = 2.5;
dot_spacing = 4;
dot_y_offset = -8;

module number_token(number) {
    // Base token
    cylinder(d = token_diameter, h = token_thickness, $fn = 64);
    
    // Raised number
    translate([0, 2, token_thickness])
        linear_extrude(height = number_height)
            text(str(number), size = number_size, font = "Liberation Sans:style=Bold", halign = "center", valign = "center");
    
    // Raised dots
    num_dots = get_dots(number);
    if (num_dots > 0) {
        start_x = -(num_dots - 1) * dot_spacing / 2;
        for (i = [0:num_dots-1]) {
            translate([start_x + i * dot_spacing, dot_y_offset, token_thickness])
                cylinder(d = dot_diameter, h = number_height, $fn = 16);
        }
    }
}

// Standard Catan number distribution
numbers = [2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12];

// Arrange in a grid (6 columns)
cols = 6;
for (i = [0:len(numbers)-1]) {
    row = floor(i / cols);
    col = i % cols;
    translate([col * spacing, -row * spacing, 0])
        number_token(numbers[i]);
}
