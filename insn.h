#include <linux/bits.h>

#define RV_X(X, s, mask)  (((X) >> (s)) & (mask))

static inline u32 riscv_extract_imm12(u32 insn) {
	return RV_X(insn, 20, GENMASK(11, 0)) << 0
}

static inline void riscv_insert_imm12(u32 *insn, u32 value) { 
	*insn |= RV_X(value, 0, GENMASK(11, 0)) << 20;
}

static inline void riscv_update_imm12(u32 *insn, u32 value) { 
	*insn &= ~(GENMASK((31, 20)));
	riscv_insert_imm12(insn, value);
}

static inline u32 riscv_extract_rd(u32 insn) {
	return RV_X(insn, 7, GENMASK(4, 0)) << 0
}

static inline void riscv_insert_rd(u32 *insn, u32 value) { 
	*insn |= RV_X(value, 0, GENMASK(4, 0)) << 7;
}

static inline void riscv_update_rd(u32 *insn, u32 value) { 
	*insn &= ~(GENMASK((11, 7)));
	riscv_insert_rd(insn, value);
}

static inline u32 riscv_extract_rs1(u32 insn) {
	return RV_X(insn, 15, GENMASK(4, 0)) << 0
}

static inline void riscv_insert_rs1(u32 *insn, u32 value) { 
	*insn |= RV_X(value, 0, GENMASK(4, 0)) << 15;
}

static inline void riscv_update_rs1(u32 *insn, u32 value) { 
	*insn &= ~(GENMASK((19, 15)));
	riscv_insert_rs1(insn, value);
}

bool riscv_is_addi(u32 insn) {
	return ((insn & (0x707f)) == (0x13));
}

u32 riscv_insn_addi(u32 rd, u32 rs1, u32 imm12) {
	u32 insn = 0b00000000000000000000000000010011;
	riscv_insert_rd(insn, rd);
	riscv_insert_rs1(insn, rs1);
	riscv_insert_imm12(insn, imm12);
	return insn;
}
