// Provide a definition of the 'toy' dialect in the ODS framework so that we
// can define our operations.
def Simile_Dialect : Dialect {
  // The namespace of our dialect, this corresponds 1-1 with the string we
  // provided in `SimileDialect::getDialectNamespace`.
  let name = "simile";

  // A short one-line summary of our dialect.
  let summary = "TODO Summary here";

  // A much longer description of our dialect.
  let description = [{TODO: Add a detailed description of the Simile dialect here.}];

  // The C++ namespace that the dialect class definition resides in.
  let cppNamespace = "simile";
}