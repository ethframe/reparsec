Parser interface and combinators
================================

.. automodule:: reparsec

Parser
------

.. autoclass:: reparsec.Parser
   :members:
   :inherited-members:
   :special-members: __add__, __or__, __lshift__, __rshift__

Helper types
------------

.. autoclass:: reparsec.TupleParser
   :members:

.. autoclass:: reparsec.Delay
   :members:

.. autoclass:: reparsec.Tuple2
   :members:

.. autoclass:: reparsec.Tuple3
   :members:

.. autoclass:: reparsec.Tuple4
   :members:

.. autoclass:: reparsec.Tuple5
   :members:

.. autoclass:: reparsec.Tuple6
   :members:

.. autoclass:: reparsec.Tuple7
   :members:

.. autoclass:: reparsec.Tuple8
   :members:

Combinators
-----------

.. autofunction:: reparsec.fmap
.. autofunction:: reparsec.bind
.. autofunction:: reparsec.seq
.. autofunction:: reparsec.seql
.. autofunction:: reparsec.seqr
.. autofunction:: reparsec.alt
.. autofunction:: reparsec.maybe
.. autofunction:: reparsec.many
.. autofunction:: reparsec.attempt
.. autofunction:: reparsec.label
.. autofunction:: reparsec.recover
.. autofunction:: reparsec.recover_with
.. autofunction:: reparsec.recover_with_fn
.. autofunction:: reparsec.sep_by
.. autofunction:: reparsec.between
.. autofunction:: reparsec.chainl1
.. autofunction:: reparsec.chainr1

Output
------

.. autoclass:: reparsec.ParseResult
   :members:

.. autoexception:: reparsec.ParseError
   :members:

.. autoclass:: reparsec.ErrorItem
   :members:

.. autoclass:: reparsec.Loc
   :members:

.. autoclass:: reparsec.Insert
   :members:

.. autoclass:: reparsec.Skip
   :members:
