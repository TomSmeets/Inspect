#define _GNU_SOURCE
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include "inspect.h"

typedef struct List List;
struct List{
    int value;
    List *next;
};

static uint32_t counter = 0;
static List *items;
char message[] = "Hello World!";

int main(void) {
    for (int i = 0; i < 10; ++i) {
        List *node = malloc(sizeof(List));
        node->value = i;
        node->next = items;
        items = node;
    }

    inspect_start(1234);

    for (;;) {
        counter++;
        printf("Counter: %u\n", counter);
        sleep(1);
    }
    return 0;
}
