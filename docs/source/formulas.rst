Building Formulas
=================

pyAirtable lets you construct formulas at runtime using Python syntax,
and will convert those formula objects into the appropriate strings when
sending them to the Airtable API.

In cases where you want to find records with fields matching a computed value,
use :func:`~pyairtable.formulas.match`:

    >>> from pyairtable.formulas import match
    >>> table.all(formula=match({"Field Name": value}))
    [...]

This is equivalent to the following:

    >>> from pyairtable.formulas import EQ, Field
    >>> table.all(formula=EQ(Field("Field Name"), value))
    [...]

pyAirtable has support for the following comparisons:

    .. list-table::

       * - :class:`pyairtable.formulas.EQ`
         - ``lval = rval``
       * - :class:`pyairtable.formulas.NE`
         - ``lval != rval``
       * - :class:`pyairtable.formulas.GT`
         - ``lval > rval``
       * - :class:`pyairtable.formulas.GTE`
         - ``lval >= rval``
       * - :class:`pyairtable.formulas.LT`
         - ``lval < rval``
       * - :class:`pyairtable.formulas.LTE`
         - ``lval <= rval``

Compound conditions
--------------------------

Formulas and conditions can be chained together if you need to create
more complex criteria:

    >>> from datetime import date
    >>> from pyairtable.formulas import AND, GTE, Field, match
    >>> formula = AND(
    ...     match("Customer", 'Alice'),
    ...     GTE(Field("Delivery Date"), date.today())
    ... )
    >>> formula
    AND(EQ(Field('Customer'), 'Alice'),
        GTE(Field('Delivery Date'), datetime.date(2023, 12, 10)))
    >>> str(formula)
    "AND({Customer}='Alice', {Delivery Date}>=DATETIME_PARSE('2023-12-10'))"

pyAirtable exports ``AND``, ``OR``, ``NOT``, and ``XOR`` for chaining conditions.
You can also use Python operators to modify and combine formulas:

    >>> from pyairtable.formulas import match
    >>> match({"Customer": "Bob"}) & ~match({"Product": "TEST"})
    AND(EQ(Field('Customer'), 'Bob'),
        NOT(EQ(Field('Product'), 'TEST')))

    .. list-table::
       :header-rows: 1

       * - Python operator
         - `Airtable equivalent <https://support.airtable.com/docs/formula-field-reference#logical-operators-and-functions-in-airtable>`__
       * - ``lval & rval``
         - ``AND(lval, rval)``
       * - ``lval | rval``
         - ``OR(lval, rval)``
       * - ``lval ^ rval``
         - ``XOR(lval, rval)``
       * - ``~rval``
         - ``NOT(rval)``

Calling functions
--------------------------

pyAirtable also exports functions that act as placeholders for calling
Airtable formula functions:

    >>> from pyairtable.formulas import Field, GTE, DATETIME_DIFF, TODAY
    >>> formula = GTE(DATETIME_DIFF(TODAY(), Field("Purchase Date"), "days"), 7)
    >>> str(formula)
    "DATETIME_DIFF(TODAY(), {Purchase Date}, 'days')>=7"

All supported functions are listed in the :mod:`pyairtable.formulas` API reference.

Escape hatch
--------------------------

If you have your own reasons to convert an arbitrary value into an Airtable expression,
you can use :meth:`~pyairtable.formula.to_formula_str`:

If you find that the functions and convenience methods provided by this module
do not meet your needs, you can use instances of ``str`` as formulas
to create arbitrary expressions:

.. code-block:: python

    # simple example using only str
    >>> table.all(formula="{Field} == 'anything'")
    [...]

    # combining Formula objects with str
    >>> formula = match({"Field": "anything"}) | "UNKNOWN_FUNCTION()=1"
    >>> str(formula)
    "OR({Field}='anything', UNKNOWN_FUNCTION()=1)"
