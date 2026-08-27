#include "liff_cli.h"

int main(int argument_count, char *arguments[]) {
    return liff_cli_run(argument_count - 1, arguments + 1, stdout, stderr);
}
