# ρhysCalc

ρhysCalc is a scientific calculator with units, constants and symbolic variables.
It has proved very useful in doing college-level physics calculations.

## Features

- REPL calculator
  ```
    > 1 + 1
  [1] 2.0 (number)
    > 1 * (2 ** 3 * 4 - 5) / 6
  [2] 4.5 (number) 
  ```
- Units
  ```
    > 3 m + 6 m
  [3] 9.0 m (distance)
    > 1/2 * 6 kg * (15 km/h)^2
  [4] 52.083333333333336 J (energy)
  ```
- Unit conversion
  ```
    > 25 m/s
  [4] 25.0 m / s (speed)
    > !as mph
      55.923407301360065 mph
    > 37 N * 5 m !as ftlb
  [5] 136.44899761629412 ftlb (energy)
  ```
- Predefined variables (`pi`, `e`, `j` by default, `!load phys` or `!load chem` for more)
  ```
    > pi
  [6] 3.141592653589793 (number)
    > !load phys
    > c
  [7] 2.99792458·10⁸ m / s (speed)
    > 1 / (4 * pi * \e_0) * 3 uC * 4 uC / (70 mm)^2
  [8] 22.010330906896773 N (force)
  ```
- Symbolic variables
  ```
    > x
  [9] x
    > x + -(yz * a_c + q_1)
  [10] x - yz * a_c - q_1
     > y := 5 m
  [11] 5.0 m (distance)
     > x + y
  [12] 5.0 m + x
     > x := 6 m / 4 ^ 1/2
  [13] 3.0 m (distance)
     > x + y
  [14] 8.0 m (distance)
  ```
- Greek letters (see `!help greek`)
  ```
     > \a + \b + \Dx + \t_\a
  [15] α + β + Δx + τ_α
  ```
- Complex numbers (basic support)
  ```
     > j
  [16] 1.0j (number)
     > (3 + 4*j) / (5 - 2*j)
  [17] (0.24137931034482757+0.896551724137931j) (number)
     > 1 / (j * 2 * pi * 50Hz * 6uF)
  [18] -530.5164769729845j Ω (resistance)
     > 2k\O + 1 / (j * 2 * pi * 50Hz * 6uF)
  [19] (2.0-0.5305164769729845j) kΩ (resistance)
  ```
- Backreferences
  ```
     > 5m + q
  [20] 5.0 m + q
     > [20]
  [21] 5.0 m + q
     > q := 3m
  [22] 3.0 m (distance)
     > [20]
  [23] 8.0 m (distance)
  ```
- Fraction output (no floats used in calculation)
  ```
     > !toggle frac
  Toggled frac on.
     > 1/16 W
  [24] 1/16 W (power)
     > ((1/2 m) ** 3 - 2/7 m**3)
  [25] -9/56 m³ (volume)
  ```