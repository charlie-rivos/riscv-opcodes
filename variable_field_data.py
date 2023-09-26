from enum import Enum, auto
from dataclasses import dataclass


class VariableFieldType(Enum):
    FLAG = auto()
    IMM = auto()
    UIMM = auto()
    NZIMM = auto()
    NZUIMM = auto()
    NZREGISTER = auto()
    REGISTER = auto()
    CSR = auto()
    NZN2REGISTER = auto()
    CREGISTER = auto()

    def is_signed(self):
        return self in {VariableFieldType.IMM, VariableFieldType.NZIMM}


class ImmType(Enum):
    HI = auto()
    LO = auto()
    UNIFIED = auto()


@dataclass(frozen=True)
class VariableField:
    type: VariableFieldType
    position: tuple[int, int]


@dataclass(frozen=True)
class ImmVariableField(VariableField):
    imm_configuration: tuple[tuple[int, int], ...]
    imm_type: ImmType


field_types: dict[str, VariableField] = {}
field_types["aq"] = VariableField(
    type=VariableFieldType.FLAG, position=(26, 26)
)
field_types["bimm12hi"] = ImmVariableField(
    type=VariableFieldType.IMM,
    position=(31, 25),
    imm_configuration=(((12, 12), (10, 5))),
    imm_type=ImmType.HI,
)
field_types["bimm12lo"] = ImmVariableField(
    type=VariableFieldType.IMM,
    position=(11, 7),
    imm_configuration=(((4, 1), (11, 11))),
    imm_type=ImmType.LO,
)
field_types["bs"] = VariableField(
    type=VariableFieldType.FLAG, position=(31, 30)
)
field_types["c_bimm9hi"] = ImmVariableField(
    type=VariableFieldType.IMM,
    position=(12, 10),
    imm_configuration=(((8, 8), (4, 3))),
    imm_type=ImmType.HI,
)
field_types["c_bimm9lo"] = ImmVariableField(
    type=VariableFieldType.IMM,
    position=(6, 2),
    imm_configuration=(((7, 6), (2, 1), (5, 5))),
    imm_type=ImmType.LO,
)
field_types["c_imm12"] = ImmVariableField(
    type=VariableFieldType.IMM,
    position=(12, 2),
    imm_configuration=(
        ((11, 11), (4, 4), (9, 8), (10, 10), (6, 6), (7, 7), (3, 1), (5, 5))
    ),
    imm_type=ImmType.UNIFIED,
)
field_types["c_imm6hi"] = ImmVariableField(
    type=VariableFieldType.IMM,
    position=(12, 12),
    imm_configuration=(((5, 5),)),
    imm_type=ImmType.HI,
)
field_types["c_imm6lo"] = ImmVariableField(
    type=VariableFieldType.IMM,
    position=(6, 2),
    imm_configuration=(((4, 0),)),
    imm_type=ImmType.LO,
)
field_types["c_index"] = VariableField(
    type=VariableFieldType.FLAG, position=(9, 2)
)
field_types["c_nzimm10hi"] = ImmVariableField(
    type=VariableFieldType.NZIMM,
    position=(12, 12),
    imm_configuration=(((9, 9),)),
    imm_type=ImmType.HI,
)
field_types["c_nzimm10lo"] = ImmVariableField(
    type=VariableFieldType.NZIMM,
    position=(6, 2),
    imm_configuration=(((4, 4), (6, 6), (8, 7), (5, 5))),
    imm_type=ImmType.LO,
)
field_types["c_nzimm18hi"] = ImmVariableField(
    type=VariableFieldType.NZIMM,
    position=(12, 12),
    imm_configuration=(((17, 17),)),
    imm_type=ImmType.HI,
)
field_types["c_nzimm18lo"] = ImmVariableField(
    type=VariableFieldType.NZIMM,
    position=(6, 2),
    imm_configuration=(((16, 12),)),
    imm_type=ImmType.LO,
)
field_types["c_nzimm6hi"] = ImmVariableField(
    type=VariableFieldType.NZIMM,
    position=(12, 12),
    imm_configuration=(((5, 5),)),
    imm_type=ImmType.HI,
)
field_types["c_nzimm6lo"] = ImmVariableField(
    type=VariableFieldType.NZIMM,
    position=(6, 2),
    imm_configuration=(((4, 0),)),
    imm_type=ImmType.LO,
)
field_types["c_nzuimm10"] = ImmVariableField(
    type=VariableFieldType.NZUIMM,
    position=(12, 5),
    imm_configuration=(((5, 4), (9, 6), (2, 2), (3, 3))),
    imm_type=ImmType.UNIFIED,
)
field_types["c_nzuimm6hi"] = ImmVariableField(
    type=VariableFieldType.NZUIMM,
    position=(12, 12),
    imm_configuration=(((5, 5),)),
    imm_type=ImmType.HI,
)
field_types["c_nzuimm6lo"] = ImmVariableField(
    type=VariableFieldType.NZUIMM,
    position=(6, 2),
    imm_configuration=(((4, 0),)),
    imm_type=ImmType.LO,
)
field_types["c_rlist"] = VariableField(
    type=VariableFieldType.FLAG, position=(7, 4)
)
field_types["c_rs1_n0"] = VariableField(
    type=VariableFieldType.NZREGISTER, position=(11, 7)
)
field_types["c_rs2"] = VariableField(
    type=VariableFieldType.REGISTER, position=(5, 1)
)
field_types["c_rs2_n0"] = VariableField(
    type=VariableFieldType.NZREGISTER, position=(6, 2)
)
field_types["c_spimm"] = ImmVariableField(
    type=VariableFieldType.UIMM,
    position=(3, 2),
    imm_configuration=(((5, 4),)),
    imm_type=ImmType.UNIFIED,
)
field_types["c_sreg1"] = ImmVariableField(
    type=VariableFieldType.UIMM,
    position=(9, 7),
    imm_configuration=(((2, 1),)),
    imm_type=ImmType.UNIFIED,
)
field_types["c_sreg2"] = ImmVariableField(
    type=VariableFieldType.UIMM,
    position=(4, 2),
    imm_configuration=(((2, 1),)),
    imm_type=ImmType.UNIFIED,
)
field_types["c_uimm1"] = ImmVariableField(
    type=VariableFieldType.UIMM,
    position=(5, 5),
    imm_configuration=(((1, 1),)),
    imm_type=ImmType.UNIFIED,
)
field_types["c_uimm10sp_s"] = ImmVariableField(
    type=VariableFieldType.UIMM,
    position=(11, 6),
    imm_configuration=(((5, 4), (9, 6))),
    imm_type=ImmType.UNIFIED,
)
field_types["c_uimm10sphi"] = ImmVariableField(
    type=VariableFieldType.UIMM,
    position=(12, 12),
    imm_configuration=(((5, 5),)),
    imm_type=ImmType.HI,
)
field_types["c_uimm10splo"] = ImmVariableField(
    type=VariableFieldType.UIMM,
    position=(6, 2),
    imm_configuration=(((4, 4), (9, 6))),
    imm_type=ImmType.LO,
)
field_types["c_uimm2"] = ImmVariableField(
    type=VariableFieldType.UIMM,
    position=(6, 5),
    imm_configuration=(((0, 0), (1, 1))),
    imm_type=ImmType.UNIFIED,
)
field_types["c_uimm7hi"] = ImmVariableField(
    type=VariableFieldType.UIMM,
    position=(12, 10),
    imm_configuration=(((5, 3),)),
    imm_type=ImmType.HI,
)
field_types["c_uimm7lo"] = ImmVariableField(
    type=VariableFieldType.UIMM,
    position=(6, 5),
    imm_configuration=(((2, 2), (6, 6))),
    imm_type=ImmType.LO,
)
field_types["c_uimm8hi"] = ImmVariableField(
    type=VariableFieldType.UIMM,
    position=(12, 10),
    imm_configuration=(((5, 3),)),
    imm_type=ImmType.HI,
)
field_types["c_uimm8lo"] = ImmVariableField(
    type=VariableFieldType.UIMM,
    position=(6, 5),
    imm_configuration=(((7, 6),)),
    imm_type=ImmType.LO,
)
field_types["c_uimm8sp_s"] = ImmVariableField(
    type=VariableFieldType.UIMM,
    position=(11, 6),
    imm_configuration=(((5, 2), (7, 6))),
    imm_type=ImmType.UNIFIED,
)
field_types["c_uimm8sphi"] = ImmVariableField(
    type=VariableFieldType.UIMM,
    position=(12, 12),
    imm_configuration=(((5, 5),)),
    imm_type=ImmType.HI,
)
field_types["c_uimm8splo"] = ImmVariableField(
    type=VariableFieldType.UIMM,
    position=(6, 2),
    imm_configuration=(((4, 2), (7, 6))),
    imm_type=ImmType.LO,
)
field_types["c_uimm9hi"] = ImmVariableField(
    type=VariableFieldType.UIMM,
    position=(12, 10),
    imm_configuration=(((5, 5), (4, 4), (8, 8))),
    imm_type=ImmType.HI,
)
field_types["c_uimm9lo"] = ImmVariableField(
    type=VariableFieldType.UIMM,
    position=(6, 5),
    imm_configuration=(((7, 6),)),
    imm_type=ImmType.LO,
)
field_types["c_uimm9sp_s"] = ImmVariableField(
    type=VariableFieldType.UIMM,
    position=(11, 6),
    imm_configuration=(((5, 3), (8, 6))),
    imm_type=ImmType.UNIFIED,
)
field_types["c_uimm9sphi"] = ImmVariableField(
    type=VariableFieldType.UIMM,
    position=(12, 12),
    imm_configuration=(((5, 5),)),
    imm_type=ImmType.HI,
)
field_types["c_uimm9splo"] = ImmVariableField(
    type=VariableFieldType.UIMM,
    position=(6, 2),
    imm_configuration=(((4, 3), (8, 6))),
    imm_type=ImmType.LO,
)
field_types["csr"] = VariableField(
    type=VariableFieldType.CSR, position=(31, 20)
)
field_types["fm"] = VariableField(
    type=VariableFieldType.FLAG, position=(31, 28)
)
field_types["imm12"] = ImmVariableField(
    type=VariableFieldType.IMM,
    position=(31, 20),
    imm_configuration=(((11, 0),)),
    imm_type=ImmType.UNIFIED,
)
field_types["imm12hi"] = ImmVariableField(
    type=VariableFieldType.IMM,
    position=(31, 25),
    imm_configuration=(((11, 5),)),
    imm_type=ImmType.HI,
)
field_types["imm12lo"] = ImmVariableField(
    type=VariableFieldType.IMM,
    position=(4, 0),
    imm_configuration=(((4, 0),)),
    imm_type=ImmType.LO,
)
field_types["imm20"] = ImmVariableField(
    type=VariableFieldType.IMM,
    position=(31, 12),
    imm_configuration=(((31, 12),)),
    imm_type=ImmType.UNIFIED,
)
field_types["imm3"] = ImmVariableField(
    type=VariableFieldType.UIMM,
    position=(22, 20),
    imm_configuration=(((2, 0),)),
    imm_type=ImmType.UNIFIED,
)
field_types["imm4"] = ImmVariableField(
    type=VariableFieldType.UIMM,
    position=(23, 20),
    imm_configuration=(((3, 0),)),
    imm_type=ImmType.UNIFIED,
)
field_types["imm5"] = ImmVariableField(
    type=VariableFieldType.UIMM,
    position=(24, 20),
    imm_configuration=(((4, 0),)),
    imm_type=ImmType.UNIFIED,
)
field_types["imm6"] = ImmVariableField(
    type=VariableFieldType.UIMM,
    position=(25, 20),
    imm_configuration=(((5, 0),)),
    imm_type=ImmType.UNIFIED,
)
field_types["jimm20"] = ImmVariableField(
    type=VariableFieldType.IMM,
    position=(31, 12),
    imm_configuration=(((20, 20), (10, 1), (11, 11), (19, 12))),
    imm_type=ImmType.UNIFIED,
)
field_types["nf"] = VariableField(
    type=VariableFieldType.FLAG, position=(31, 29)
)
field_types["pred"] = VariableField(
    type=VariableFieldType.FLAG, position=(27, 24)
)
field_types["rd"] = VariableField(
    type=VariableFieldType.REGISTER, position=(11, 7)
)
field_types["rd_n0"] = VariableField(
    type=VariableFieldType.NZREGISTER, position=(11, 7)
)
field_types["rd_n2"] = VariableField(
    type=VariableFieldType.NZN2REGISTER, position=(11, 7)
)
field_types["rd_p"] = VariableField(
    type=VariableFieldType.CREGISTER, position=(9, 7)
)
field_types["rd_rs1_n0"] = VariableField(
    type=VariableFieldType.NZREGISTER, position=(11, 7)
)
field_types["rd_rs1_p"] = VariableField(
    type=VariableFieldType.REGISTER, position=(9, 7)
)
field_types["rl"] = VariableField(
    type=VariableFieldType.FLAG, position=(25, 25)
)
field_types["rm"] = VariableField(
    type=VariableFieldType.FLAG, position=(14, 12)
)
field_types["rnum"] = VariableField(
    type=VariableFieldType.FLAG, position=(23, 20)
)
field_types["rs1"] = VariableField(
    type=VariableFieldType.REGISTER, position=(19, 15)
)
field_types["rs1_n0"] = VariableField(
    type=VariableFieldType.NZREGISTER, position=(11, 7)
)
field_types["rs1_p"] = VariableField(
    type=VariableFieldType.CREGISTER, position=(9, 7)
)
field_types["rs2"] = VariableField(
    type=VariableFieldType.REGISTER, position=(24, 20)
)
field_types["rs2_p"] = VariableField(
    type=VariableFieldType.REGISTER, position=(9, 7)
)
field_types["rs3"] = VariableField(
    type=VariableFieldType.REGISTER, position=(31, 27)
)
field_types["shamtd"] = ImmVariableField(
    type=VariableFieldType.IMM,
    position=(25, 20),
    imm_configuration=(((5, 0),)),
    imm_type=ImmType.UNIFIED,
)
field_types["shamtq"] = ImmVariableField(
    type=VariableFieldType.IMM,
    position=(26, 20),
    imm_configuration=(((6, 0),)),
    imm_type=ImmType.UNIFIED,
)
field_types["shamtw"] = ImmVariableField(
    type=VariableFieldType.IMM,
    position=(24, 20),
    imm_configuration=(((4, 0),)),
    imm_type=ImmType.UNIFIED,
)
field_types["simm5"] = VariableField(
    type=VariableFieldType.IMM, position=(19, 15)
)
field_types["succ"] = VariableField(
    type=VariableFieldType.FLAG, position=(23, 19)
)
field_types["vd"] = VariableField(
    type=VariableFieldType.REGISTER, position=(11, 7)
)
field_types["vm"] = VariableField(
    type=VariableFieldType.FLAG, position=(25, 25)
)
field_types["vs1"] = VariableField(
    type=VariableFieldType.REGISTER, position=(19, 15)
)
field_types["vs2"] = VariableField(
    type=VariableFieldType.REGISTER, position=(24, 20)
)
field_types["vs3"] = VariableField(
    type=VariableFieldType.REGISTER, position=(11, 7)
)
field_types["wd"] = VariableField(
    type=VariableFieldType.FLAG, position=(26, 16)
)
field_types["zimm"] = ImmVariableField(
    type=VariableFieldType.UIMM,
    position=(19, 15),
    imm_configuration=(((4, 0),)),
    imm_type=ImmType.UNIFIED,
)
field_types["zimm10"] = ImmVariableField(
    type=VariableFieldType.UIMM,
    position=(29, 20),
    imm_configuration=(((9, 0),)),
    imm_type=ImmType.UNIFIED,
)
field_types["zimm11"] = ImmVariableField(
    type=VariableFieldType.UIMM,
    position=(30, 20),
    imm_configuration=(((10, 0),)),
    imm_type=ImmType.UNIFIED,
)
field_types["zimm5"] = ImmVariableField(
    type=VariableFieldType.UIMM,
    position=(19, 15),
    imm_configuration=(((4, 0),)),
    imm_type=ImmType.UNIFIED,
)
field_types["zimm6hi"] = ImmVariableField(
    type=VariableFieldType.UIMM,
    position=(26, 26),
    imm_configuration=(((5, 5),)),
    imm_type=ImmType.HI,
)
field_types["zimm6lo"] = ImmVariableField(
    type=VariableFieldType.UIMM,
    position=(19, 15),
    imm_configuration=(((4, 0),)),
    imm_type=ImmType.LO,
)
