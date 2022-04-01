import json
import operator as op
import re
from collections import deque
from io import BytesIO
from typing import Union, Iterable

import matplotlib.pyplot as plt
import numpy as np
from mpmath import mp


# Function util

def _is_identifier(token:str):
    """ Whether a piece of text is a valid variable """
    return token.isidentifier()

def _is_token_defined(token:str, scope:dict=None):
    """ Whether a token is defined in the current scope """
    return (scope is not None and token in scope) \
           or token in constants \
           or token in functions \
           or token in custom_functions

class Function:
    """ A Function definition. A function definition has a name and various
        arguments. When __call__ is invoked, the function is evaluated with the given
        arguments. """

    def __init__(self, name:str, args:Union[str, Iterable, None], function:callable, f_args:Union[str, Iterable]='', f_arg_cls=None):
        """
        Create a new function definition.
        :param name: Name of the function.
        :param args: List of arguemtns. If None, argument length checking will be disabled.
        :param function: Callable evaluator function.
        :param f_args: Arguments in args that are functions. F_args will be passed a
                       Postfix token list rather than a value.
        :param f_arg_cls: Override the default ArgumentFunction class to implement custom behavior.
        """
        self.name = name
        self.args = args
        self.f_args = f_args
        self._function = function
        self._f_arg_cls = f_arg_cls or ArgumentFunction
        self.scope = {}

    @property
    def signature(self):
        if self.args is None:
            return '{}(?)'.format(self.name)
        else:
            return '{}({})'.format(self.name, ', '.join(self.args))

    def is_f_arg(self, i):
        return self.args is not None \
               and 0 <= i < len(self.args) \
               and self.args[i] in self.f_args

    def ArgumentFunction(self, arg_index, postfix):
        """ Create a new ArgumentFunction off of this Function. """
        return self._f_arg_cls(self, arg_index, postfix)

    def __str__(self):
        return self.signature

    def __repr__(self):
        return "{0.__class__.__name__}('{0.name}', '{0.args}', '{0.f_args}')".format(self)

    def __call__(self, *args):
        if self.args is not None and len(args) != len(self.args):
            # Wrong number of arguments
            raise TypeError('Function {} expected {} argument{} but {} {} given.'.format(
                self.signature,
                len(self.args),
                's' if len(self.args) != 1 else '',
                len(args),
                'were' if len(args) != 1 else 'was'
            ))
        else:
            return self._function(*args)

class ArgumentFunction(Function):
    """ A Function definition that exists as an f_arg to another Function. """

    def __init__(self, parent, arg_index, postfix):
        self.parent = parent
        self.arg_index = arg_index
        self._evaluator = PostfixEvaluator(postfix)
        super().__init__(self.arg, None, None)

    @property
    def arg(self):
        return self.parent.args[self.arg_index]

    @property
    def signature(self):
        return "argument '{0.arg}' of {0.parent.signature}".format(self)
        # return '{}[{}]'.format(self.arg, ' '.join(map(str, self.postfix)))

    @property
    def postfix(self) -> list:
        return self._evaluator.postfix

    @postfix.setter
    def postfix(self, pf:list):
        self._evaluator.postfix = pf

    def _search_variables(self):
        return sorted(
            token for token in self.postfix
            if isinstance(token, str)
               and _is_identifier(token)
               and not _is_token_defined(token, self.scope)
        )

    def _zip_variables(self, args):
        variables = self._search_variables()
        if len(variables) != len(args):
            raise SyntaxError(
                "{} argument{} passed to {}, but {} variable{} found: {}".format(
                    len(args), ' was' if len(args) == 1 else 's were',
                    str(self),
                    len(variables), ' was' if len(variables) == 1 else 's were',
                    ', '.join(variables)
                ))
        return dict(zip(variables, args))

    def __call__(self, *args):
        scope = self.scope.copy()
        scope.update(self._zip_variables(args))
        return self._evaluator.evaluate(substitutions=scope)

    def __repr__(self):
        return "{0.__class__.__name__}('{0.parent}', '{0.arg_index}')".format(self)

class CustomFunction(Function):
    """ A Function definition created by a user. Signature is parsed from an expression
        of the form 'f(a,b,c)=expression' """

    def __init__(self, expression):
        signature, self.exp = expression.replace(' ', '').split('=', 1)

        parts = signature.split('(', 1)
        name = parts[0]
        if len(parts) > 1: args = ''.join(parts[1].replace(')', '', 1).split(','))
        else: args = ''
        if args == '': # no parameter function
            args = ''

        tokens = Tokenizer(self.exp).tokenize()
        self._verify(name, args, tokens)

        self._evaluator = PostfixEvaluator(InfixToPostfix(tokens).convert())
        def evaluate(scope, *a):
            scope = {**scope, **dict(zip(args, a))}
            return self._evaluator.evaluate(scope)
        super().__init__(name, args, function=evaluate, scoped=True)

    def __str__(self):
        return '{} = {}'.format(self.signature, self.exp)

    def __repr__(self):
        return "{0.__class__.__name__}('{0.name}', '{0.args}', '{0.f_args}', '{0.exp}')".format(self)

    @staticmethod
    def _verify(name, args, tokens):
        if name in functions:
            raise PermissionError("Cannot redefine built-in function: " + name)
        elif name in constants or name == 'ans':
            raise PermissionError("Cannot redefine built-in constant: " + name)
        elif not _is_identifier(name):
            raise SyntaxError("Invalid function name: " + name)

        for arg in args:
            if arg == name:
                raise ValueError('Function argument name cannot be the same as the function name: ' + arg)
            elif not _is_identifier(name):
                raise SyntaxError('Invalid function argument name: ' + arg)
            elif arg in constants or arg in functions or arg in custom_functions:
                raise PermissionError('Argument name is already a defined function/constant name: ' + arg)

        for token in tokens:
            if isinstance(token, str) and _is_identifier(token) \
                    and token not in args \
                    and _is_token_defined(token):
                raise NameError('Token is not defined in function signature: ' + token)


# Parser & Evaluator

class Tokenizer:
    def __init__(self, expression, scope=None):
        if isinstance(expression, list):
            # Already tokenized
            self.exp = expression
        else:
            self.exp = expression.replace(' ', '')
        self.pos = 0
        self.scope = scope or {}

    def tokenize(self):
        if isinstance(self.exp, list):
            # Already tokenized
            return self.exp

        result = []
        current = self.next()
        while current is not None:
            if isinstance(current, list):
                result.extend(current)
            else:
                result.append(current)
            current = self.next()
        self._add_implicit_multiplication(result)
        return result

    def next(self):
        ch = self.ch()
        if ch is None:
            return None
        elif ch == '(' or ch == ')' or ch == ',':
            return self.tokenize_single(ch)
        elif ch.isdigit() or ch == '.':
            return self.tokenize_number(ch)
        elif ch == '-':
            return self.tokenize_unary(ch)
        elif ch in operators:
            return self.tokenize_single(ch)
        elif _is_identifier(ch):
            return self.tokenize_identifier(ch)
        else:
            msg = f"Unknown token at char '{ch}'"
            if ch == '|': msg += "\n(For absolute value, use 'abs(x)' instead of '|x|')"
            elif ch == '!': msg += "\n(For factorials, use 'fact(n)' instead of 'n!')"
            raise SyntaxError(msg)

    def ch(self, pos=None):
        if pos is None:
            pos = self.pos
        return self.exp[pos] if 0 <= pos < len(self.exp) else None

    def tokenize_single(self, ch):
        self.pos += 1
        return ch

    def tokenize_number(self, ch):
        endpos = self.pos + 1
        end = self.ch(endpos)
        while end and end.isdigit() or end == '.':
            endpos += 1
            end = self.ch(endpos)
        token = self.exp[self.pos:endpos]
        self.pos = endpos
        return token

    def tokenize_unary(self, ch):
        prev = self.ch(self.pos - 1)
        next = self.ch(self.pos + 1)
        if not prev or prev == '(' or prev == ',' or prev in operators:
            # Negation
            if _is_identifier(next) or next.isdigit() or next == '(':
                self.pos += 1
                return '¬'
            else:
                raise SyntaxError("Invalid negation")
        else:
            # Subtraction
            return self.tokenize_single(ch)

    def tokenize_identifier(self, ch):
        endpos = self.pos + 1
        # end = self.ch(endpos)
        while endpos < len(self.exp) and _is_identifier(self.exp[self.pos:endpos+1]):
            endpos += 1
        token = self._split_identifiers(self.exp[self.pos:endpos])
        self.pos = endpos
        return token

    def _split_identifiers(self, chars):
        """ Separates a group of concatenated identifiers """
        if len(chars) == 1:
            return [chars]

        end = 1
        for i in range(1, len(chars) + 1):
            part = chars[:i]
            if part in functions \
                    or part in constants \
                    or part in custom_functions \
                    or part in self.scope \
                    or re.fullmatch(r'^[a-zA-Z_][0-9]+$', part): # eat numbers to maintain valid names
                end = i

        result = [chars[:end]]
        if end == len(chars): return result
        else: return result + self._split_identifiers(chars[end:])

    @staticmethod
    def _add_implicit_multiplication(tokens):
        i = 0
        while i < len(tokens)-1:
            cur = tokens[i]
            nxt = tokens[i + 1]
            if cur not in operators \
                    and cur not in functions \
                    and (cur not in custom_functions or len(custom_functions[cur].args) == 0) \
                    and cur != '(' and cur != ',' and cur != '¬':
                if nxt not in operators and nxt != ')' and nxt != ',':
                    tokens.insert(i+1, '*')
                    i += 1
            i += 1


class InfixToPostfix:
    _precedence = {
        '+': 1, '-': 1,
        '*': 3, '/': 3, '%': 3,
        '^': 4,
        'func': 2, ',': 0
    }

    def __init__(self, infix):
        self.tokens = Tokenizer(infix).tokenize()

    def convert(self):
        output = deque()
        output_tmp = deque()
        stack = deque()
        arg_indices = deque()

        for i in range(len(self.tokens)):
            token = self.tokens[i]
            num = self._get_mpf(token)
            oper = operators.get(token)
            func = functions.get(token)
            cfunc = custom_functions.get(token)

            if oper or func or cfunc:
                # Operator/function
                while len(stack) > 0 and self._not_greater(stack, token):
                    # Output operators on the stack of lower precedence
                    output.append(stack.pop())
                # Add the operator / function to the stack
                if func: stack.append(func)
                else: stack.append(token)
                # If the token is a function, track the argument index
                if func or cfunc:
                    arg_indices.append([func or cfunc, 0])
                    if (func or cfunc).is_f_arg(0):
                        output, output_tmp = output_tmp, output

            elif token == '(':
                # Opening parenthesis
                stack.append(token)

            elif token == ')':
                # Closing parenthesis
                while len(stack) > 0 and stack[-1] != '(':
                    # Search for (
                    output.append(stack.pop())
                if len(stack) == 0:
                    # No ( was in the stack
                    raise SyntaxError("Mismatching parenthesis (open < close)")
                else:
                    # Pop the parenthesis
                    stack.pop()
                    if len(stack) > 0 and (isinstance(stack[-1], Function) or stack[-1] in custom_functions):
                        f, ix = arg_indices.pop()
                        if f.is_f_arg(ix):
                            output, output_tmp = output_tmp, output
                            self._append_arg_func(f, ix, output, output_tmp)
                        # If the parenthesis follows a function, output it
                        output.append(stack.pop())

            elif token == ',':
                # Multivariable function
                while len(stack) > 0 and stack[-1] != ',' and stack[-1] != '(':
                    # Search for (
                    output.append(stack.pop())
                stack.append(',')

                if arg_indices:
                    # Check for function argument. If this argument is a function
                    # argument then output will contain the postfix for it.
                    # Append a new ArgumentFunction to the output.
                    f, ix = arg_indices[-1]
                    if f.is_f_arg(ix):
                        output, output_tmp = output_tmp, output
                        self._append_arg_func(f, ix, output, output_tmp)
                    arg_indices[-1][1] += 1 # Move to next argument

                if arg_indices:
                    # If the next argument is also a function, swap the outputs back
                    if arg_indices[-1][0].is_f_arg(arg_indices[-1][1]):
                        output, output_tmp = output_tmp, output

            elif token == '¬':
                # Unary negation operator
                # Convert to multiply by -1
                output.append(mp.mpf(-1))
                stack.append('*')

            elif _is_identifier(token):
                # Variable operand
                # Output the variable
                output.append(token)

            elif num is not None:
                # Numeric operand
                output.append(num)

            else:
                # Invalid token
                raise SyntaxError("Unknown token: " + str(token))

        while len(stack) > 0:
            output.append(stack.pop())

        if '(' in output:
            # Leftover parenthesis
            raise SyntaxError("Mismatching parenthesis (open > close)")

        if len(output) == 0:
            # output is empty
            raise SyntaxError("Expression is empty.")

        return list(output)

    @classmethod
    def _not_greater(cls, stack, token):
        a = cls._precedence.get(token)
        # if token in _functions or token in custom_functions:
        #     a = cls._precedence['func']
        b = cls._precedence.get(stack[-1])
        if stack[-1] in functions or stack[-1] in custom_functions:
            b = cls._precedence['func']
        return a is not None and b is not None and a <= b

    @staticmethod
    def _get_mpf(token):
        try:
            return mp.mpf(token)
        except ValueError:
            return None

    @staticmethod
    def _append_arg_func(f, ix, output, f_output):
        """ Create an argument function """
        output.append(f.ArgumentFunction(ix, list(f_output)))
        f_output.clear()


class PostfixEvaluator:
    def __init__(self, postfix):
        self.postfix = list(postfix)

    def evaluate(self, substitutions=None):
        global _answer

        if substitutions is None:
            substitutions = {}
        subs = {
            **constants,
            **substitutions
        }
        stack = deque()

        for token in self.postfix:

            if isinstance(token, (mp.mpf, mp.mpc, ArgumentFunction)):
                # Numerical operand
                stack.append(token)

            elif token == 'ans':
                # Use previous answer
                stack.append(_answer)

            elif token in subs:
                # Variable operand
                num = mp.mpc(subs[token])
                if mp.im(num) == 0:
                    num = mp.re(num)
                stack.append(num)

            elif token in operators:
                # Operator
                # Pop 2 numbers from the stack
                b = self._pop(stack)
                a = self._pop(stack)
                try:
                    # Evaluate the operator
                    result = operators[token](a, b)
                    stack.append(result)
                except ValueError:
                    # Operator inputs are invalid (ex. factorials only accept positive integers)
                    raise ValueError(f"Domain error for operator '{token}' at {a} {token} {b}")

            elif token == ',':
                # Function argument separator
                b = self._pop(stack)
                a = self._pop(stack)
                if not isinstance(a, list): a = [a]
                if not isinstance(b, list): b = [b]
                stack.append(a + b)

            elif isinstance(token, Function) or token in custom_functions:
                # Function
                if token in custom_functions: func = custom_functions[token]
                else: func = token

                if len(stack) == 0 or len(func.args) == 0:
                    args = []
                else:
                    args = self._pop(stack)
                    if not isinstance(args, list):
                        args = [args]

                try:
                    # Evaluate the function
                    func.scope = substitutions
                    for arg in args:
                        if isinstance(arg, ArgumentFunction):
                            arg.scope = substitutions
                    result = func(*args)
                    stack.append(result)
                except ValueError:
                    # Function inputs are invalid
                    raise ValueError(f"Domain error in function {func.signature} for argument(s) {args}")
            else:
                # Invalid token
                raise SyntaxError(f"Undefined token '{token}'")

        if len(stack) > 1:
            raise SyntaxError('Leftover tokens after evaluation. Make sure all operators and functions have valid inputs.')

        _answer = self._pop(stack)
        return _answer

    @staticmethod
    def _pop(stack):
        if len(stack) == 0:
            raise SyntaxError('Ran out of tokens during evaluation. Make sure all operators and functions have valid '
                              'inputs, and check implicit multiplication')
        return stack.pop()


# Calculus

class DifferentialFunctionArgument(ArgumentFunction):
    def __init__(self, parent, arg_index, postfix):
        super().__init__(parent, arg_index, postfix)
        self.differential = None

    def _zip_variables(self, args):
        print('d', self.differential)
        return {self.differential: args[0]}

class DifferentialDefinitionArgument(ArgumentFunction):
    def __call__(self):
        diff = ''
        for token in self.postfix:
            if isinstance(token, str) and token.isalpha():
                diff += token
            elif token != '*':
                raise SyntaxError("Invalid differential variable: {}".format(token))
        return diff[1:]

class DefiniteIntegralFunction(Function):
    def __init__(self, name:str, args:Union[str, Iterable]):
        super().__init__(name, args, self.evaluate, f_args='fd')

    def ArgumentFunction(self, arg_index, postfix):
        if self.args[arg_index] == 'd':
            return DifferentialDefinitionArgument(self, arg_index, postfix)
        else:
            return DifferentialFunctionArgument(self, arg_index, postfix)

    @staticmethod
    def evaluate(f, d, a, b):
        print('integrate:', ' '.join(f.postfix), d, f.scope, a, b, sep='\n\t')
        result = mp.quad(f, [a, b])
        if mp.im(result) == 0:
            result = mp.re(result)
        return result

class DerivativeFunction(Function):
    def __init__(self, name:str, args:Union[str, Iterable]):
        super().__init__(name, args, self.evaluate, f_args='fd')

    def ArgumentFunction(self, arg_index, postfix):
        if self.args[arg_index] == 'd':
            return DifferentialDefinitionArgument(self, arg_index, postfix)
        else:
            return DifferentialFunctionArgument(self, arg_index, postfix)

    @staticmethod
    def evaluate(f, d, x, n=1):
        f.differential = d()
        print('diff:', f, f.differential, x, n)
        result = mp.diff(f, x, int(n))
        if mp.im(result) == 0:
            result = mp.re(result)
        return result

class LimitFunction:
    def __init__(self, expression, var):
        self.evaluator = PostfixEvaluator(InfixToPostfix(expression).convert())
        self.var = var

    def evaluate(self, x, direction):
        pass

class LimitFunctionMP(LimitFunction):
    def evaluate(self, x, direction):
        try:
            result = mp.limit(lambda x1: self.evaluator.evaluate({self.var: x1}), x, direction, exp=True)
            if mp.im(result) == 0:
                result = mp.re(result)
        except ZeroDivisionError:
            result = "DNE"
        return result


# Usage methods

def define_custom(expression):
    func = CustomFunction(expression)

    # func(*(mp.rand() for _ in range(len(func.args)))) # test function
    custom_functions[func.name] = func

    return func

def remove_custom(name):
    if name in functions:
        raise PermissionError("Cannot remove built-in function: " + name)
    elif name in constants:
        raise PermissionError("Cannot remove build-in constant: " + name)
    elif name not in custom_functions:
        raise NameError("Custom function does not exist: " + name)
    else:
        return custom_functions.pop(name)

def load_custom_defined(filename):
    with open(filename, 'r') as f:
        data = json.loads(f.read())
        for exp in data['custom_functions']:
            func = CustomFunction(exp)
            custom_functions[func.name] = func

def save_custom_defined(filename):
    with open(filename, 'w') as f:
        data = {'custom_functions': []}
        for func in custom_functions.values():
            data['custom_functions'].append(str(func))
        f.write(json.dumps(data, indent=4))

def plot(name, xlow, xhigh, n):
    if name in custom_functions:
        func = custom_functions[name]
    elif name in functions:
        func = functions[name]
    else:
        raise NameError("Function does not exist: " + name)

    if len(func.args) != 1:
        raise ValueError('Function is not one dimensional: {} takes {} arguments'.format(func.signature, len(func.args)))

    x = np.linspace(xlow, xhigh, n)
    y = np.empty((1, len(x)))[0]

    for i in range(len(x)):
        result = func(x[i])
        if isinstance(result, mp.mpc):
            if mp.im(result) == 0: result = mp.re(result)
            else: raise ValueError("Cannot plot imaginary output at x={}: {}".format(x[i], result))
        elif isinstance(result, list):
            raise ValueError("Cannot plot multiple outputs at {}={}: {}".format(func.args[0], x[i], result))
        y[i] = float(result)

    fig, ax = plt.subplots(1, 1)
    ax.plot(x, y)
    ax.set_xlim(xlow, xhigh)
    ax.set_xlabel(func.args[0])
    ax.set_ylabel(func.signature)
    ax.set_title('{} on [{}, {}]'.format(str(func), xlow, xhigh))
    ax.grid(True)

    buf = BytesIO()
    fig.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)

    return buf

def format_value(val):
    if isinstance(val, list):
        return '[' + ', '.join(format_value(a) for a in val) + ']'
    else:
        return str(val)

def set_ans(answer):
    global _answer
    _answer = answer


# Non built-in functions

def permutation(n, k):
    return mp.fac(n) / mp.fac(n - k)

def random_between(low, high):
    return mp.rand() * (high - low) + low

def cartesian_to_polar(x, y):
    return [mp.hypot(x, y), mp.atan2(y, x)]

def polar_to_cartesian(r, theta):
    return [r*mp.cos(theta), r*mp.sin(theta)]

def cartesian_to_cylindrical(x, y, z):
    return [mp.hypot(x, y), mp.atan2(y, x), z]

def cartesian_to_spherical(x, y, z):
    r = mp.sqrt(x*x + y*y + z*z)
    return [r, mp.atan2(y, x), mp.acos(z/r)]

def cylindrical_to_cartesian(rho, phi, z):
    return [rho*mp.cos(phi), rho*mp.sin(phi), z]

def cylindrical_to_spherical(rho, phi, z):
    return [mp.hypot(rho, z), phi, mp.atan2(rho, z)]

def spherical_to_cartesian(r, theta, phi):
    return [r*mp.sin(phi)*mp.cos(theta), r*mp.sin(theta)*mp.sin(phi), r*mp.cos(phi)]

def spherical_to_cylindrical(r, theta, phi):
    return [r*mp.sin(phi), theta, r*mp.cos(phi)]


# Built-in definitions

operators = {
    '+': op.add,
    '-': op.sub,
    '*': op.mul,
    '/': op.truediv,
    '^': op.pow,
    '%': op.mod,
}
constants = {
    'pi': mp.pi,
    'π': mp.pi,
    'e': mp.e,
    'i': mp.j,
    'inf': mp.inf
}
functions = {
    # Basic Functions
    'neg':   Function('neg', 'x', op.neg),
    'abs':   Function('abs', 'x', abs),
    'rad':   Function('rad', 'θ', mp.radians),
    'deg':   Function('deg', 'θ', mp.degrees),
    'round': Function('round', 'x', round),
    'floor': Function('floor', 'x', mp.floor),
    'ceil':  Function('ceil', 'x', mp.ceil),

    # Roots & Complex Functions
    'sqrt':  Function('sqrt', 'x', mp.sqrt),
    'root':  Function('root', 'xn', mp.root),
    'hypot': Function('hypot', 'ab', mp.hypot),
    'real':  Function('real', 'c', mp.re),
    'imag':  Function('imag', 'c', mp.im),

    # Trigonometric Functions
    'sin':  Function('sin', 'θ', mp.sin),
    'cos':  Function('cos', 'θ', mp.cos),
    'tan':  Function('tan', 'θ', mp.tan),
    'sec':  Function('sec', 'θ', mp.sec),
    'csc':  Function('csc', 'θ', mp.csc),
    'cot':  Function('cot', 'θ', mp.cot),
    'asin': Function('asin', 'x', mp.asin),
    'acos': Function('acos', 'x', mp.acos),
    'atan': Function('atan', 'x', mp.atan),

    # Hyperbolic Functions
    'sinh': Function('sinh', 'x', mp.sinh),
    'cosh': Function('cosh', 'x', mp.cosh),
    'tanh': Function('tanh', 'x', mp.tanh),

    # Exponential & Logarithmic Functions
    'exp':  Function('exp', 'x', mp.exp),
    'ln':   Function('ln', 'x', mp.ln),
    'log':  Function('log', 'x', mp.log10),
    'logb': Function('logb', 'xb', mp.log),

    # Combinatorial & Random Functions
    'fact':        Function('fact', 'x', mp.fac),
    'P':           Function('P', 'nk', permutation),
    'C':           Function('C', 'nk', mp.binomial),
    'fib':         Function('fib', 'n', mp.fib),
    'rand':        Function('rand', '', mp.rand),
    'randbetween': Function('randbetween', 'ab', random_between),

    # Calculus
    'int':    DefiniteIntegralFunction('int', 'fdab'),
    'deriv':  DerivativeFunction('deriv', 'fdx'),
    'nderiv': DerivativeFunction('nderiv', 'fdxn'),

    # Coordinate System Conversion Functions
    'polar':  Function('polar', 'xy', cartesian_to_polar),
    'rect':   Function('rect', 'rθ', polar_to_cartesian),
    'crtcyl': Function('crtcyl', 'xyz', cartesian_to_cylindrical),
    'crtsph': Function('crtsph', 'xyz', cartesian_to_spherical),
    'cylcrt': Function('cylcrt', 'ρφz', cylindrical_to_cartesian),
    'cylsph': Function('cylsph', 'ρφz', cylindrical_to_spherical),
    'sphcrt': Function('sphcrt', 'rθφ', spherical_to_cartesian),
    'sphcyl': Function('sphcyl', 'rθφ', spherical_to_cylindrical),
}

custom_functions = {}
_answer = mp.mpf(0)
