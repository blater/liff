package liff.core;

/** A random-selection or headword-search request. */
public sealed interface Request permits RandomRequest, SearchRequest {}
