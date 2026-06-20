/*
 * SneakOut scheduling engine.
 *
 * Data structures used (per assignment requirements):
 *   - HASHMAP : day-name -> array of ClassEntry   (chained hash table)
 *   - ARRAY   : ClassEntry[] for each day's timeline (dynamic array)
 *   - SET     : unique subject codes per day / per week (hash set, chained)
 *
 * The program is invoked by the Flask backend as a subprocess.
 * It prints a single JSON object to stdout.
 *
 * Usage:
 *   ./scheduler today <HH:MM> <DayName>
 *   ./scheduler day <DayName>
 *   ./scheduler week
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define BUCKETS 32
#define MAX_ENTRIES 16

/* ---------------------------------------------------------- */
/* Core record                                                 */
/* ---------------------------------------------------------- */
typedef struct {
    char id[8];
    char start[6];
    char end[6];
    char subject[64];
    char code[16];
    char room[16];
    char faculty[32];
    char type[12]; /* lecture | lab | tutorial | free */
} ClassEntry;

/* ---------------------------------------------------------- */
/* ARRAY: dynamic array of ClassEntry per day                  */
/* ---------------------------------------------------------- */
typedef struct {
    ClassEntry items[MAX_ENTRIES];
    int count;
} ClassArray;

static void array_push(ClassArray *arr, ClassEntry e) {
    if (arr->count < MAX_ENTRIES) arr->items[arr->count++] = e;
}

/* ---------------------------------------------------------- */
/* HASHMAP: day name -> ClassArray*  (separate chaining)       */
/* ---------------------------------------------------------- */
typedef struct MapNode {
    char key[8];
    ClassArray value;
    struct MapNode *next;
} MapNode;

typedef struct {
    MapNode *buckets[BUCKETS];
} HashMap;

static unsigned hash_str(const char *s) {
    unsigned h = 5381;
    while (*s) h = ((h << 5) + h) + (unsigned char)(*s++);
    return h % BUCKETS;
}

static ClassArray *map_get_or_create(HashMap *m, const char *key) {
    unsigned h = hash_str(key);
    for (MapNode *n = m->buckets[h]; n; n = n->next)
        if (strcmp(n->key, key) == 0) return &n->value;
    MapNode *node = calloc(1, sizeof(MapNode));
    strncpy(node->key, key, sizeof(node->key) - 1);
    node->next = m->buckets[h];
    m->buckets[h] = node;
    return &node->value;
}

static ClassArray *map_get(HashMap *m, const char *key) {
    unsigned h = hash_str(key);
    for (MapNode *n = m->buckets[h]; n; n = n->next)
        if (strcmp(n->key, key) == 0) return &n->value;
    return NULL;
}

/* ---------------------------------------------------------- */
/* SET: unique subject codes (separate chaining hash set)      */
/* ---------------------------------------------------------- */
typedef struct SetNode {
    char value[16];
    struct SetNode *next;
} SetNode;

typedef struct {
    SetNode *buckets[BUCKETS];
    int size;
} StrSet;

static int set_add(StrSet *s, const char *v) {
    if (!v || v[0] == '\0') return 0;
    unsigned h = hash_str(v);
    for (SetNode *n = s->buckets[h]; n; n = n->next)
        if (strcmp(n->value, v) == 0) return 0; /* already present */
    SetNode *node = malloc(sizeof(SetNode));
    strncpy(node->value, v, sizeof(node->value) - 1);
    node->value[sizeof(node->value) - 1] = '\0';
    node->next = s->buckets[h];
    s->buckets[h] = node;
    s->size++;
    return 1;
}

/* ---------------------------------------------------------- */
/* Seed data: builds the week HashMap                          */
/* ---------------------------------------------------------- */
static void add(HashMap *m, const char *day, const char *id,
                 const char *start, const char *end, const char *subject,
                 const char *code, const char *room, const char *faculty,
                 const char *type) {
    ClassEntry e = {0};
    strncpy(e.id, id, sizeof(e.id) - 1);
    strncpy(e.start, start, sizeof(e.start) - 1);
    strncpy(e.end, end, sizeof(e.end) - 1);
    strncpy(e.subject, subject, sizeof(e.subject) - 1);
    strncpy(e.code, code, sizeof(e.code) - 1);
    strncpy(e.room, room, sizeof(e.room) - 1);
    strncpy(e.faculty, faculty, sizeof(e.faculty) - 1);
    strncpy(e.type, type, sizeof(e.type) - 1);
    array_push(map_get_or_create(m, day), e);
}

static void seed(HashMap *m) {
    add(m, "Mon", "m1", "08:00", "09:00", "Engineering Mathematics III", "MA301", "A-201", "Prof. S. Mehta", "lecture");
    add(m, "Mon", "m2", "09:00", "11:00", "Computer Networks Lab", "CS303L", "Lab-3", "Prof. A. Sharma", "lab");
    add(m, "Mon", "m3", "11:00", "12:00", "", "", "", "", "free");
    add(m, "Mon", "m4", "12:00", "13:00", "Data Structures", "CS201", "B-104", "Dr. R. Iyer", "lecture");
    add(m, "Mon", "m5", "14:00", "15:00", "Operating Systems", "CS302", "C-301", "Dr. P. Nair", "lecture");

    add(m, "Tue", "t1", "09:00", "10:00", "DBMS", "CS304", "A-105", "Prof. V. Gupta", "lecture");
    add(m, "Tue", "t2", "10:00", "11:00", "", "", "", "", "free");
    add(m, "Tue", "t3", "11:00", "13:00", "DSA Lab", "CS201L", "Lab-2", "Dr. R. Iyer", "lab");
    add(m, "Tue", "t4", "14:00", "15:00", "Software Engineering", "CS305", "B-201", "Dr. K. Reddy", "lecture");

    add(m, "Wed", "w1", "08:00", "09:00", "Engineering Mathematics III", "MA301", "A-201", "Prof. S. Mehta", "lecture");
    add(m, "Wed", "w2", "09:00", "10:00", "OS Tutorial", "CS302T", "A-105", "Dr. P. Nair", "tutorial");
    add(m, "Wed", "w3", "10:00", "11:00", "Data Structures", "CS201", "B-104", "Dr. R. Iyer", "lecture");
    add(m, "Wed", "w4", "11:00", "13:00", "DBMS Lab", "CS304L", "Lab-4", "Prof. V. Gupta", "lab");
    add(m, "Wed", "w5", "14:00", "15:00", "Computer Networks", "CS303", "C-301", "Prof. A. Sharma", "lecture");
    add(m, "Wed", "w6", "16:00", "17:00", "Software Engineering", "CS305", "B-201", "Dr. K. Reddy", "lecture");

    add(m, "Thu", "th1", "10:00", "11:00", "DBMS Tutorial", "CS304T", "A-105", "Prof. V. Gupta", "tutorial");
    add(m, "Thu", "th2", "11:00", "13:00", "", "", "", "", "free");
    add(m, "Thu", "th3", "13:00", "14:00", "", "", "", "", "free");
    add(m, "Thu", "th4", "15:00", "16:00", "Engineering Mathematics III", "MA301", "A-201", "Prof. S. Mehta", "lecture");

    add(m, "Fri", "f1", "09:00", "10:00", "Computer Networks", "CS303", "C-301", "Prof. A. Sharma", "lecture");
    add(m, "Fri", "f2", "10:00", "11:00", "Operating Systems", "CS302", "C-301", "Dr. P. Nair", "lecture");
    add(m, "Fri", "f3", "11:00", "12:00", "", "", "", "", "free");
    add(m, "Fri", "f4", "13:00", "15:00", "Software Lab", "CS305L", "Lab-1", "Dr. K. Reddy", "lab");
    add(m, "Fri", "f5", "16:00", "17:00", "Data Structures", "CS201", "B-104", "Dr. R. Iyer", "lecture");

    add(m, "Sat", "sa1", "08:00", "09:00", "DS Tutorial", "CS201T", "A-105", "Dr. R. Iyer", "tutorial");
    add(m, "Sat", "sa2", "09:00", "10:00", "Engineering Mathematics III", "MA301", "A-201", "Prof. S. Mehta", "lecture");
}

/* ---------------------------------------------------------- */
/* JSON helpers                                                 */
/* ---------------------------------------------------------- */
static void jesc(const char *s, char *out, size_t outlen) {
    size_t j = 0;
    for (size_t i = 0; s[i] && j < outlen - 2; i++) {
        if (s[i] == '"' || s[i] == '\\') out[j++] = '\\';
        out[j++] = s[i];
    }
    out[j] = '\0';
}

static void print_entry(ClassEntry *e, int is_current) {
    char buf[128];
    printf("{");
    printf("\"id\":\"%s\",", e->id);
    printf("\"startTime\":\"%s\",", e->start);
    printf("\"endTime\":\"%s\",", e->end);
    jesc(e->subject, buf, sizeof(buf)); printf("\"subject\":\"%s\",", buf);
    jesc(e->code, buf, sizeof(buf));    printf("\"code\":\"%s\",", buf);
    jesc(e->room, buf, sizeof(buf));    printf("\"room\":\"%s\",", buf);
    jesc(e->faculty, buf, sizeof(buf)); printf("\"faculty\":\"%s\",", buf);
    printf("\"type\":\"%s\",", e->type);
    printf("\"isCurrent\":%s", is_current ? "true" : "false");
    printf("}");
}

static int to_mins(const char *t) {
    int h, m;
    sscanf(t, "%d:%d", &h, &m);
    return h * 60 + m;
}

/* ---------------------------------------------------------- */
/* Commands                                                     */
/* ---------------------------------------------------------- */
static void cmd_day(HashMap *m, const char *day, const char *now_hhmm) {
    ClassArray *arr = map_get(m, day);
    int now = now_hhmm ? to_mins(now_hhmm) : -1;

    StrSet codes;
    memset(&codes, 0, sizeof(codes));

    int classCount = 0, freeCount = 0, labCount = 0;
    int currentIdx = -1, nextIdx = -1;

    if (arr) {
        for (int i = 0; i < arr->count; i++) {
            ClassEntry *e = &arr->items[i];
            int isFree = strcmp(e->type, "free") == 0;
            if (isFree) freeCount++; else classCount++;
            if (strcmp(e->type, "lab") == 0) labCount++;
            if (!isFree) set_add(&codes, e->code);

            if (now >= 0 && !isFree) {
                int s = to_mins(e->start), en = to_mins(e->end);
                if (now >= s && now < en) currentIdx = i;
                else if (now < s && nextIdx == -1) nextIdx = i;
            }
        }
    }

    printf("{\"day\":\"%s\",", day);
    printf("\"classCount\":%d,\"freeCount\":%d,\"labCount\":%d,\"uniqueSubjects\":%d,",
           classCount, freeCount, labCount, codes.size);

    printf("\"timeline\":[");
    if (arr) {
        for (int i = 0; i < arr->count; i++) {
            if (i) printf(",");
            print_entry(&arr->items[i], i == currentIdx);
        }
    }
    printf("],");

    printf("\"current\":");
    if (currentIdx >= 0) print_entry(&arr->items[currentIdx], 1); else printf("null");
    printf(",\"next\":");
    if (nextIdx >= 0) print_entry(&arr->items[nextIdx], 0); else printf("null");

    if (currentIdx >= 0) {
        int s = to_mins(arr->items[currentIdx].start);
        int en = to_mins(arr->items[currentIdx].end);
        int pct = (now - s) * 100 / (en - s > 0 ? en - s : 1);
        if (pct < 0) pct = 0; if (pct > 100) pct = 100;
        printf(",\"progressPercent\":%d", pct);
    } else {
        printf(",\"progressPercent\":0");
    }
    printf("}\n");
}

static void cmd_week(HashMap *m) {
    const char *days[] = {"Mon", "Tue", "Wed", "Thu", "Fri", "Sat"};
    StrSet weekCodes;
    memset(&weekCodes, 0, sizeof(weekCodes));
    int totalClasses = 0, totalFree = 0, totalLabs = 0;

    printf("{\"days\":[");
    for (int d = 0; d < 6; d++) {
        ClassArray *arr = map_get(m, days[d]);
        int classCount = 0, freeCount = 0, labCount = 0;
        if (arr) {
            for (int i = 0; i < arr->count; i++) {
                ClassEntry *e = &arr->items[i];
                int isFree = strcmp(e->type, "free") == 0;
                if (isFree) { freeCount++; totalFree++; }
                else { classCount++; totalClasses++; set_add(&weekCodes, e->code); }
                if (strcmp(e->type, "lab") == 0) { labCount++; totalLabs++; }
            }
        }
        if (d) printf(",");
        printf("{\"day\":\"%s\",\"classCount\":%d,\"freeCount\":%d,\"labCount\":%d}",
               days[d], classCount, freeCount, labCount);
    }
    printf("],\"totalClasses\":%d,\"totalFree\":%d,\"totalLabs\":%d,\"uniqueSubjects\":%d}\n",
           totalClasses, totalFree, totalLabs, weekCodes.size);
}

int main(int argc, char **argv) {
    HashMap weekMap;
    memset(&weekMap, 0, sizeof(weekMap));
    seed(&weekMap);

    if (argc < 2) {
        fprintf(stderr, "usage: scheduler <today|day|week> [args]\n");
        return 1;
    }

    if (strcmp(argv[1], "today") == 0 && argc >= 4) {
        cmd_day(&weekMap, argv[3], argv[2]);
    } else if (strcmp(argv[1], "day") == 0 && argc >= 3) {
        cmd_day(&weekMap, argv[2], NULL);
    } else if (strcmp(argv[1], "week") == 0) {
        cmd_week(&weekMap);
    } else {
        fprintf(stderr, "bad arguments\n");
        return 1;
    }
    return 0;
}
