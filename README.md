# PyFuncify

## Introduction

Pyfuncify contains useful functions for the use primarily in Python-based AWS Lambda serverless functions.  The majority of the functions are generic (rather than AWS-specifc), however, all these functions have been useful in building distributed serverless functions, based on local patterns.

The objective is to collect together useful functions found during the development of Lambda services.

For example, we have used monads (PyMonad) extensively for building composable pipelines and avoiding raising exceptions.  In the monad lib there is also a try decorator than wraps exception-throwing functions.  We have a simple circuit-breaker mechanism, and a method of performing an oauth client credentials grant.

This lib is not an AWS Lambda paved road or framework.  Consider it as a collection of helpers.