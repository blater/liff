package liff.core;

/** Complete result of resolving a dictionary request. */
public sealed interface Outcome permits Found, DidYouMean, NotFound {}
