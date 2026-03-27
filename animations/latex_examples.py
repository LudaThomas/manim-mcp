from manim import *


class BasicFormulas(Scene):
    """Render common mathematical formulas with MathTex."""

    def construct(self):
        # Euler's identity
        euler = MathTex(r"e^{i\pi} + 1 = 0", font_size=60)
        euler_label = Text("Euler's Identity", font_size=28, color=GREY)
        euler_group = VGroup(euler_label, euler).arrange(DOWN, buff=0.3)
        euler_group.to_edge(UP)

        # Pythagorean theorem
        pyth = MathTex(r"a^2 + b^2 = c^2", font_size=60)
        pyth_label = Text("Pythagorean Theorem", font_size=28, color=GREY)
        pyth_group = VGroup(pyth_label, pyth).arrange(DOWN, buff=0.3)

        # Quadratic formula
        quad = MathTex(
            r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}", font_size=60
        )
        quad_label = Text("Quadratic Formula", font_size=28, color=GREY)
        quad_group = VGroup(quad_label, quad).arrange(DOWN, buff=0.3)
        quad_group.to_edge(DOWN)

        everything = VGroup(euler_group, pyth_group, quad_group).arrange(DOWN, buff=0.8)
        everything.move_to(ORIGIN)

        self.play(Write(euler_group), run_time=2)
        self.wait(0.5)
        self.play(Write(pyth_group), run_time=2)
        self.wait(0.5)
        self.play(Write(quad_group), run_time=2)
        self.wait(2)


class ColoredEquation(Scene):
    """Demonstrate coloring individual parts of an equation."""

    def construct(self):
        # MathTex splits on double braces for coloring
        equation = MathTex(
            r"E", r"=", r"m", r"c^2",
            font_size=96,
        )
        equation[0].set_color(YELLOW)   # E
        equation[2].set_color(BLUE)     # m
        equation[3].set_color(RED)      # c^2

        self.play(Write(equation), run_time=2)
        self.wait(1)

        # Animate individual parts
        self.play(equation[3].animate.scale(1.5), run_time=0.5)
        self.play(equation[3].animate.scale(1 / 1.5), run_time=0.5)
        self.wait(1)


class EquationTransform(Scene):
    """Animate transformations between equations."""

    def construct(self):
        eq1 = MathTex(r"x^2 + 2x + 1", font_size=72)
        eq2 = MathTex(r"(x + 1)^2", font_size=72)
        eq3 = MathTex(r"x = -1", font_size=72)

        self.play(Write(eq1))
        self.wait(1)
        self.play(TransformMatchingTex(eq1, eq2))
        self.wait(1)
        self.play(TransformMatchingTex(eq2, eq3))
        self.wait(2)


class CalculusShowcase(Scene):
    """Showcase calculus notation: limits, derivatives, integrals, sums."""

    def construct(self):
        limit = MathTex(
            r"\lim_{x \to 0} \frac{\sin x}{x} = 1",
            font_size=48,
        )
        derivative = MathTex(
            r"\frac{d}{dx}\left[x^n\right] = nx^{n-1}",
            font_size=48,
        )
        integral = MathTex(
            r"\int_0^\infty e^{-x^2} \, dx = \frac{\sqrt{\pi}}{2}",
            font_size=48,
        )
        series = MathTex(
            r"\sum_{n=0}^{\infty} \frac{x^n}{n!} = e^x",
            font_size=48,
        )

        equations = VGroup(limit, derivative, integral, series)
        equations.arrange(DOWN, buff=0.6)
        equations.move_to(ORIGIN)

        for eq in equations:
            self.play(Write(eq), run_time=1.5)
            self.wait(0.5)

        self.wait(2)


class MatrixExample(Scene):
    """Render matrices and linear algebra notation."""

    def construct(self):
        matrix = MathTex(
            r"\begin{bmatrix} a & b \\ c & d \end{bmatrix}"
            r"\begin{bmatrix} x \\ y \end{bmatrix}"
            r"="
            r"\begin{bmatrix} ax + by \\ cx + dy \end{bmatrix}",
            font_size=48,
        )

        det = MathTex(
            r"\det(A) = \begin{vmatrix} a & b \\ c & d \end{vmatrix} = ad - bc",
            font_size=48,
        )

        group = VGroup(matrix, det).arrange(DOWN, buff=1)
        group.move_to(ORIGIN)

        self.play(Write(matrix), run_time=2)
        self.wait(1)
        self.play(Write(det), run_time=2)
        self.wait(2)


class TextWithMath(Scene):
    """Mix regular text with inline math using Tex (not MathTex)."""

    def construct(self):
        line1 = Tex(
            r"The area of a circle is $A = \pi r^2$",
            font_size=44,
        )
        line2 = Tex(
            r"where $r$ is the radius and $\pi \approx 3.14159$",
            font_size=44,
        )
        line3 = Tex(
            r"For $r = 3$, we get $A = 9\pi \approx 28.27$",
            font_size=44,
        )

        lines = VGroup(line1, line2, line3).arrange(DOWN, buff=0.5)
        lines.move_to(ORIGIN)

        for line in lines:
            self.play(Write(line), run_time=1.5)
            self.wait(0.5)

        self.wait(2)
