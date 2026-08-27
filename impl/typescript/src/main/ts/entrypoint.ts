import { run, type TextSink } from "./cli";

declare const process: {
    readonly argv: readonly string[];
    readonly stdout: TextSink;
    readonly stderr: TextSink;
    exitCode?: number;
};

process.exitCode = run(process.argv.slice(2), process.stdout, process.stderr);
