#ifndef CODEC_CPU_H
#define CODEC_CPU_H
#include <stdint.h>
#ifdef _WIN32
#define CODEC_CPU_API __declspec(dllexport)
#else
#define CODEC_CPU_API __attribute__((visibility("default")))
#endif
#ifdef __cplusplus
extern "C" {
#endif

typedef struct codec_cpu codec_cpu;
/* floooh/chips pin layout; address 0..15, data 16..23. */
#define CODEC_PIN_M1 (1ULL<<24)
#define CODEC_PIN_MREQ (1ULL<<25)
#define CODEC_PIN_IORQ (1ULL<<26)
#define CODEC_PIN_RD (1ULL<<27)
#define CODEC_PIN_WR (1ULL<<28)
#define CODEC_PIN_HALT (1ULL<<29)
#define CODEC_PIN_INT (1ULL<<30)
#define CODEC_PIN_NMI (1ULL<<32)
#define CODEC_PIN_WAIT (1ULL<<33)
#define CODEC_PIN_RFSH (1ULL<<34)
#define CODEC_PIN_RETI (1ULL<<38)
#define CODEC_PIN_DATA(p,v) (((p)&~0xff0000ULL)|((uint64_t)(uint8_t)(v)<<16))

/* Set/reset is an instruction-boundary operation, not a mid-instruction
 * checkpoint. Getter PC is the next instruction at an opdone boundary and the
 * core's current PC otherwise. halt is read-only diagnostic: nonzero halt input
 * is rejected. q is restored after priming the initial fetch. This is not a
 * complete internal-state checkpoint. The raw phase exposes decoder step. */
typedef struct {
    uint32_t pc,af,bc,de,hl,sp,ix,iy,af2,bc2,de2,hl2,wz,i,r,iff1,iff2,im,halt,q;
} codec_cpu_registers;
typedef struct {
    uint64_t cpu_tstates,wait_tstates,pins;
    uint32_t step,pc,bc,de,hl,sp,addr,wz,opcode,i,r,af;
} codec_cpu_phase;
/* The pin service runs AFTER each original CPU T, with absolute physical time
 * cpu_tstates+wait_tstates. Initial prefetch is at time 0. Return serviced data
 * and input-line pins for the next CPU T. Native C callbacks avoid Python per
 * byte. Attaching either hook disables fused execution. A pin callback alone
 * cannot model Spectrum internal-cycle contention: see phase hook below. */
typedef uint64_t (*codec_cpu_bus)(void *context,uint64_t pins,uint64_t physical_tstate);
/* Optional BEFORE-T hook. Its explicit delay holds core state, increments only
 * wait_tstates, and may update sampled pins. The bus owns verified cycle-start
 * annotations and advancement during that delay. No contention model is
 * inferred from stale bus pins; unannotated integration is uncontended. */
typedef uint32_t (*codec_cpu_before_t)(void *context,const codec_cpu_phase *phase,uint64_t *pins);
typedef struct {
    uint32_t source,input_bytes,output,output_bytes,caller_stack;
    const uint8_t *expected_output; /* Retain until guards are replaced/disabled. */
} codec_cpu_guards;
typedef struct {
    uint64_t cpu_tstates,wait_tstates,error,error_address,error_value;
    uint64_t input_cursor,output_cursor,stack_bytes,memory_writes;
} codec_cpu_status;

CODEC_CPU_API uint32_t codec_cpu_abi_version(void);
CODEC_CPU_API codec_cpu *codec_cpu_create(void);
CODEC_CPU_API void codec_cpu_destroy(codec_cpu *cpu);
CODEC_CPU_API uint8_t *codec_cpu_memory(codec_cpu *cpu);
/* ABI2: return 1 on valid boundary initialization; return 0 and set status
 * error5 for unsupported halt input, q>255, or null register pointer. */
CODEC_CPU_API uint32_t codec_cpu_set_registers(codec_cpu *cpu,const codec_cpu_registers *registers);
CODEC_CPU_API void codec_cpu_get_registers(codec_cpu *cpu,codec_cpu_registers *registers);
CODEC_CPU_API void codec_cpu_get_phase(codec_cpu *cpu,codec_cpu_phase *phase);
CODEC_CPU_API void codec_cpu_get_status(codec_cpu *cpu,codec_cpu_status *status);
CODEC_CPU_API void codec_cpu_set_bus(codec_cpu *cpu,codec_cpu_bus bus,void *context);
CODEC_CPU_API void codec_cpu_set_before_t(codec_cpu *cpu,codec_cpu_before_t hook,void *context);
CODEC_CPU_API void codec_cpu_set_lines(codec_cpu *cpu,uint64_t mask,uint64_t value);
CODEC_CPU_API uint64_t codec_cpu_pins(codec_cpu *cpu);
CODEC_CPU_API uint64_t codec_cpu_tick(codec_cpu *cpu,uint64_t input_pins);
/* CPU budget excludes explicit phase-hook waits. Return 0=stop PC reached,
 * 1=budget exhausted, 2=guard error. fast requests fused flat-bus slices;
 * hooks/active asynchronous input lines automatically select original ticks. */
CODEC_CPU_API uint32_t codec_cpu_run_to_pc(codec_cpu *cpu,uint32_t stop_pc,uint64_t budget,uint32_t fast);
/* Execute at least one instruction/repeating-block iteration, even if its
 * next PC equals its entry PC. Same 0=complete,1=budget,2=guard status. */
CODEC_CPU_API uint32_t codec_cpu_step_instruction(codec_cpu *cpu,uint64_t budget,uint32_t fast);
CODEC_CPU_API uint64_t codec_cpu_fused_slices(codec_cpu *cpu);
/* Permissions: bit0 permits flat reads (code/stack), bit1 permits flat writes
 * (embedded operands). All other accesses must satisfy sequential input,
 * already-published history, exact output bytes or the caller stack bounds.
 * Caller validates disjoint live allocations; guards require flat bus mode. */
CODEC_CPU_API uint32_t codec_cpu_set_guards(codec_cpu *cpu,const codec_cpu_guards *guards,const uint8_t *permissions);
CODEC_CPU_API void codec_cpu_disable_guards(codec_cpu *cpu);
/* Optional C-native JP/JR NZ/Z/NC/C counters, sampled at instruction entry. */
CODEC_CPU_API void codec_cpu_watch_branch(codec_cpu *cpu,uint32_t address,uint32_t enabled);
CODEC_CPU_API void codec_cpu_branch_counts(codec_cpu *cpu,uint32_t address,uint64_t *not_taken,uint64_t *taken);
#ifdef __cplusplus
}
#endif
#endif
