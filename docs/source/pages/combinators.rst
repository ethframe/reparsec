Parser interface and combinators
================================


Parser
------

.. autoclass:: reparsec.Parser
   :members:
   :special-members: __add__, __or__, __lshift__, __rshift__

.. autoclass:: reparsec.ParseResult
   :members:

.. autoexception:: reparsec.ParseError
   :members:

.. autoclass:: reparsec.ErrorItem
   :members:

.. autoclass:: reparsec.Delay
   :show-inheritance:
   :members:


Combinators
-----------

.. automodule:: reparsec
   :members: fmap, bind, seq, seql, seqr, alt, maybe, many, attempt, label,
      insert_on_error, sep_by, between, chainl1, chainr1


Combinators for layout-sensitive parsing
----------------------------------------

.. automodule:: reparsec.layout
   :members:
