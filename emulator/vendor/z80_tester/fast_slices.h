/* ALTERED GENERATED SOURCE: derived from pinned floooh/chips z80.h by
 * z80-tester generate_fast_decoder.py; flat RAM reads use codec_flat_read.
 * Copyright (c) 2021 Andre Weissflog; zlib/libpng license, see LICENSE.
 * This is not an unmodified upstream header. */
#define _sa(ab)             pins=_z80_set_ab(pins,ab)
#define _sax(ab,x)          pins=_z80_set_ab_x(pins,ab,x)
#define _sad(ab,d)          pins=_z80_set_ab_db(pins,ab,d)
#define _sadx(ab,d,x)       pins=_z80_set_ab_db_x(pins,ab,d,x)
#define _gd()               _z80_get_db(pins)

// high level helper macros
#define _goto(n)        cpu->step=n;goto step_to
#define _fetch()        goto fetch_next
#define _fetch_dd()     pins=_z80_fetch_dd(cpu,pins);
#define _fetch_fd()     pins=_z80_fetch_fd(cpu,pins);
#define _fetch_ed()     pins=_z80_fetch_ed(cpu,pins);
#define _fetch_cb()     pins=_z80_fetch_cb(cpu,pins);
#define _mread(ab)      _sax(ab,Z80_MREQ|Z80_RD)
#define _mwrite(ab,d)   _sadx(ab,d,Z80_MREQ|Z80_WR)
#define _ioread(ab)     _sax(ab,Z80_IORQ|Z80_RD)
#define _iowrite(ab,d)  _sadx(ab,d,Z80_IORQ|Z80_WR)
#define _wait()         {if(pins&Z80_WAIT)goto step_to;}
#define _cc_nz          (!(cpu->f&Z80_ZF))
#define _cc_z           (cpu->f&Z80_ZF)
#define _cc_nc          (!(cpu->f&Z80_CF))
#define _cc_c           (cpu->f&Z80_CF)
#define _cc_po          (!(cpu->f&Z80_PF))
#define _cc_pe          (cpu->f&Z80_PF)
#define _cc_p           (!(cpu->f&Z80_SF))
#define _cc_m           (cpu->f&Z80_SF)



#undef _mread
#undef _mwrite
#undef _ioread
#undef _iowrite
#undef _wait
#undef _fetch
#define _mread(ab) do { _sax(ab,Z80_MREQ|Z80_RD); Z80_SET_DATA(pins,codec_flat_read(b,Z80_GET_ADDR(pins))); } while(0)
#define _mwrite(ab,d) do { _sadx(ab,d,Z80_MREQ|Z80_WR); ++b->writes; BOARD_MEMORY_WRITE(b,Z80_GET_ADDR(pins),Z80_GET_DATA(pins)); } while(0)
#define _ioread(ab) do { _sax(ab,Z80_IORQ|Z80_RD); Z80_SET_DATA(pins,BOARD_INPUT(b,pins)); } while(0)
#define _iowrite(ab,d) do { _sadx(ab,d,Z80_IORQ|Z80_WR); board_emit(b,b->ticks+elapsed,Z80_GET_ADDR(pins),Z80_GET_DATA(pins)); } while(0)
#define _wait() ((void)0)

/* Run through one fetch boundary without dispatching every individual T.
 * The caller reserves 32 T and excludes pending/active interrupt sequences.
 * Exact partial runs and asynchronous INT/NMI retain the original tick path. */
static uint32_t board_fast_slice(board *b) {
    z80_t *cpu = &b->cpu;
    uint64_t pins = b->pins;
    uint32_t elapsed = 0;
fast_dispatch:
    switch (cpu->step) {
        case 0: goto fast_0;
        case 1: goto fast_1;
        case 2: goto fast_2;
        case 3: goto fast_3;
        case 4: goto fast_4;
        case 5: goto fast_5;
        case 6: goto fast_6;
        case 7: goto fast_7;
        case 8: goto fast_8;
        case 9: goto fast_9;
        case 10: goto fast_10;
        case 11: goto fast_11;
        case 12: goto fast_12;
        case 13: goto fast_13;
        case 14: goto fast_14;
        case 15: goto fast_15;
        case 16: goto fast_16;
        case 17: goto fast_17;
        case 18: goto fast_18;
        case 19: goto fast_19;
        case 20: goto fast_20;
        case 21: goto fast_21;
        case 22: goto fast_22;
        case 23: goto fast_23;
        case 24: goto fast_24;
        case 25: goto fast_25;
        case 26: goto fast_26;
        case 27: goto fast_27;
        case 28: goto fast_28;
        case 29: goto fast_29;
        case 30: goto fast_30;
        case 31: goto fast_31;
        case 32: goto fast_32;
        case 33: goto fast_33;
        case 34: goto fast_34;
        case 35: goto fast_35;
        case 36: goto fast_36;
        case 37: goto fast_37;
        case 38: goto fast_38;
        case 39: goto fast_39;
        case 40: goto fast_40;
        case 41: goto fast_41;
        case 42: goto fast_42;
        case 43: goto fast_43;
        case 44: goto fast_44;
        case 45: goto fast_45;
        case 46: goto fast_46;
        case 47: goto fast_47;
        case 48: goto fast_48;
        case 49: goto fast_49;
        case 50: goto fast_50;
        case 51: goto fast_51;
        case 52: goto fast_52;
        case 53: goto fast_53;
        case 54: goto fast_54;
        case 55: goto fast_55;
        case 56: goto fast_56;
        case 57: goto fast_57;
        case 58: goto fast_58;
        case 59: goto fast_59;
        case 60: goto fast_60;
        case 61: goto fast_61;
        case 62: goto fast_62;
        case 63: goto fast_63;
        case 64: goto fast_64;
        case 65: goto fast_65;
        case 66: goto fast_66;
        case 67: goto fast_67;
        case 68: goto fast_68;
        case 69: goto fast_69;
        case 70: goto fast_70;
        case 71: goto fast_71;
        case 72: goto fast_72;
        case 73: goto fast_73;
        case 74: goto fast_74;
        case 75: goto fast_75;
        case 76: goto fast_76;
        case 77: goto fast_77;
        case 78: goto fast_78;
        case 79: goto fast_79;
        case 80: goto fast_80;
        case 81: goto fast_81;
        case 82: goto fast_82;
        case 83: goto fast_83;
        case 84: goto fast_84;
        case 85: goto fast_85;
        case 86: goto fast_86;
        case 87: goto fast_87;
        case 88: goto fast_88;
        case 89: goto fast_89;
        case 90: goto fast_90;
        case 91: goto fast_91;
        case 92: goto fast_92;
        case 93: goto fast_93;
        case 94: goto fast_94;
        case 95: goto fast_95;
        case 96: goto fast_96;
        case 97: goto fast_97;
        case 98: goto fast_98;
        case 99: goto fast_99;
        case 100: goto fast_100;
        case 101: goto fast_101;
        case 102: goto fast_102;
        case 103: goto fast_103;
        case 104: goto fast_104;
        case 105: goto fast_105;
        case 106: goto fast_106;
        case 107: goto fast_107;
        case 108: goto fast_108;
        case 109: goto fast_109;
        case 110: goto fast_110;
        case 111: goto fast_111;
        case 112: goto fast_112;
        case 113: goto fast_113;
        case 114: goto fast_114;
        case 115: goto fast_115;
        case 116: goto fast_116;
        case 117: goto fast_117;
        case 118: goto fast_118;
        case 119: goto fast_119;
        case 120: goto fast_120;
        case 121: goto fast_121;
        case 122: goto fast_122;
        case 123: goto fast_123;
        case 124: goto fast_124;
        case 125: goto fast_125;
        case 126: goto fast_126;
        case 127: goto fast_127;
        case 128: goto fast_128;
        case 129: goto fast_129;
        case 130: goto fast_130;
        case 131: goto fast_131;
        case 132: goto fast_132;
        case 133: goto fast_133;
        case 134: goto fast_134;
        case 135: goto fast_135;
        case 136: goto fast_136;
        case 137: goto fast_137;
        case 138: goto fast_138;
        case 139: goto fast_139;
        case 140: goto fast_140;
        case 141: goto fast_141;
        case 142: goto fast_142;
        case 143: goto fast_143;
        case 144: goto fast_144;
        case 145: goto fast_145;
        case 146: goto fast_146;
        case 147: goto fast_147;
        case 148: goto fast_148;
        case 149: goto fast_149;
        case 150: goto fast_150;
        case 151: goto fast_151;
        case 152: goto fast_152;
        case 153: goto fast_153;
        case 154: goto fast_154;
        case 155: goto fast_155;
        case 156: goto fast_156;
        case 157: goto fast_157;
        case 158: goto fast_158;
        case 159: goto fast_159;
        case 160: goto fast_160;
        case 161: goto fast_161;
        case 162: goto fast_162;
        case 163: goto fast_163;
        case 164: goto fast_164;
        case 165: goto fast_165;
        case 166: goto fast_166;
        case 167: goto fast_167;
        case 168: goto fast_168;
        case 169: goto fast_169;
        case 170: goto fast_170;
        case 171: goto fast_171;
        case 172: goto fast_172;
        case 173: goto fast_173;
        case 174: goto fast_174;
        case 175: goto fast_175;
        case 176: goto fast_176;
        case 177: goto fast_177;
        case 178: goto fast_178;
        case 179: goto fast_179;
        case 180: goto fast_180;
        case 181: goto fast_181;
        case 182: goto fast_182;
        case 183: goto fast_183;
        case 184: goto fast_184;
        case 185: goto fast_185;
        case 186: goto fast_186;
        case 187: goto fast_187;
        case 188: goto fast_188;
        case 189: goto fast_189;
        case 190: goto fast_190;
        case 191: goto fast_191;
        case 192: goto fast_192;
        case 193: goto fast_193;
        case 194: goto fast_194;
        case 195: goto fast_195;
        case 196: goto fast_196;
        case 197: goto fast_197;
        case 198: goto fast_198;
        case 199: goto fast_199;
        case 200: goto fast_200;
        case 201: goto fast_201;
        case 202: goto fast_202;
        case 203: goto fast_203;
        case 204: goto fast_204;
        case 205: goto fast_205;
        case 206: goto fast_206;
        case 207: goto fast_207;
        case 208: goto fast_208;
        case 209: goto fast_209;
        case 210: goto fast_210;
        case 211: goto fast_211;
        case 212: goto fast_212;
        case 213: goto fast_213;
        case 214: goto fast_214;
        case 215: goto fast_215;
        case 216: goto fast_216;
        case 217: goto fast_217;
        case 218: goto fast_218;
        case 219: goto fast_219;
        case 220: goto fast_220;
        case 221: goto fast_221;
        case 222: goto fast_222;
        case 223: goto fast_223;
        case 224: goto fast_224;
        case 225: goto fast_225;
        case 226: goto fast_226;
        case 227: goto fast_227;
        case 228: goto fast_228;
        case 229: goto fast_229;
        case 230: goto fast_230;
        case 231: goto fast_231;
        case 232: goto fast_232;
        case 233: goto fast_233;
        case 234: goto fast_234;
        case 235: goto fast_235;
        case 236: goto fast_236;
        case 237: goto fast_237;
        case 238: goto fast_238;
        case 239: goto fast_239;
        case 240: goto fast_240;
        case 241: goto fast_241;
        case 242: goto fast_242;
        case 243: goto fast_243;
        case 244: goto fast_244;
        case 245: goto fast_245;
        case 246: goto fast_246;
        case 247: goto fast_247;
        case 248: goto fast_248;
        case 249: goto fast_249;
        case 250: goto fast_250;
        case 251: goto fast_251;
        case 252: goto fast_252;
        case 253: goto fast_253;
        case 254: goto fast_254;
        case 255: goto fast_255;
        case 256: goto fast_256;
        case 257: goto fast_257;
        case 258: goto fast_258;
        case 259: goto fast_259;
        case 260: goto fast_260;
        case 261: goto fast_261;
        case 262: goto fast_262;
        case 263: goto fast_263;
        case 264: goto fast_264;
        case 265: goto fast_265;
        case 266: goto fast_266;
        case 267: goto fast_267;
        case 268: goto fast_268;
        case 269: goto fast_269;
        case 270: goto fast_270;
        case 271: goto fast_271;
        case 272: goto fast_272;
        case 273: goto fast_273;
        case 274: goto fast_274;
        case 275: goto fast_275;
        case 276: goto fast_276;
        case 277: goto fast_277;
        case 278: goto fast_278;
        case 279: goto fast_279;
        case 280: goto fast_280;
        case 281: goto fast_281;
        case 282: goto fast_282;
        case 283: goto fast_283;
        case 284: goto fast_284;
        case 285: goto fast_285;
        case 286: goto fast_286;
        case 287: goto fast_287;
        case 288: goto fast_288;
        case 289: goto fast_289;
        case 290: goto fast_290;
        case 291: goto fast_291;
        case 292: goto fast_292;
        case 293: goto fast_293;
        case 294: goto fast_294;
        case 295: goto fast_295;
        case 296: goto fast_296;
        case 297: goto fast_297;
        case 298: goto fast_298;
        case 299: goto fast_299;
        case 300: goto fast_300;
        case 301: goto fast_301;
        case 302: goto fast_302;
        case 303: goto fast_303;
        case 304: goto fast_304;
        case 305: goto fast_305;
        case 306: goto fast_306;
        case 307: goto fast_307;
        case 308: goto fast_308;
        case 309: goto fast_309;
        case 310: goto fast_310;
        case 311: goto fast_311;
        case 312: goto fast_312;
        case 313: goto fast_313;
        case 314: goto fast_314;
        case 315: goto fast_315;
        case 316: goto fast_316;
        case 317: goto fast_317;
        case 318: goto fast_318;
        case 319: goto fast_319;
        case 320: goto fast_320;
        case 321: goto fast_321;
        case 322: goto fast_322;
        case 323: goto fast_323;
        case 324: goto fast_324;
        case 325: goto fast_325;
        case 326: goto fast_326;
        case 327: goto fast_327;
        case 328: goto fast_328;
        case 329: goto fast_329;
        case 330: goto fast_330;
        case 331: goto fast_331;
        case 332: goto fast_332;
        case 333: goto fast_333;
        case 334: goto fast_334;
        case 335: goto fast_335;
        case 336: goto fast_336;
        case 337: goto fast_337;
        case 338: goto fast_338;
        case 339: goto fast_339;
        case 340: goto fast_340;
        case 341: goto fast_341;
        case 342: goto fast_342;
        case 343: goto fast_343;
        case 344: goto fast_344;
        case 345: goto fast_345;
        case 346: goto fast_346;
        case 347: goto fast_347;
        case 348: goto fast_348;
        case 349: goto fast_349;
        case 350: goto fast_350;
        case 351: goto fast_351;
        case 352: goto fast_352;
        case 353: goto fast_353;
        case 354: goto fast_354;
        case 355: goto fast_355;
        case 356: goto fast_356;
        case 357: goto fast_357;
        case 358: goto fast_358;
        case 359: goto fast_359;
        case 360: goto fast_360;
        case 361: goto fast_361;
        case 362: goto fast_362;
        case 363: goto fast_363;
        case 364: goto fast_364;
        case 365: goto fast_365;
        case 366: goto fast_366;
        case 367: goto fast_367;
        case 368: goto fast_368;
        case 369: goto fast_369;
        case 370: goto fast_370;
        case 371: goto fast_371;
        case 372: goto fast_372;
        case 373: goto fast_373;
        case 374: goto fast_374;
        case 375: goto fast_375;
        case 376: goto fast_376;
        case 377: goto fast_377;
        case 378: goto fast_378;
        case 379: goto fast_379;
        case 380: goto fast_380;
        case 381: goto fast_381;
        case 382: goto fast_382;
        case 383: goto fast_383;
        case 384: goto fast_384;
        case 385: goto fast_385;
        case 386: goto fast_386;
        case 387: goto fast_387;
        case 388: goto fast_388;
        case 389: goto fast_389;
        case 390: goto fast_390;
        case 391: goto fast_391;
        case 392: goto fast_392;
        case 393: goto fast_393;
        case 394: goto fast_394;
        case 395: goto fast_395;
        case 396: goto fast_396;
        case 397: goto fast_397;
        case 398: goto fast_398;
        case 399: goto fast_399;
        case 400: goto fast_400;
        case 401: goto fast_401;
        case 402: goto fast_402;
        case 403: goto fast_403;
        case 404: goto fast_404;
        case 405: goto fast_405;
        case 406: goto fast_406;
        case 407: goto fast_407;
        case 408: goto fast_408;
        case 409: goto fast_409;
        case 410: goto fast_410;
        case 411: goto fast_411;
        case 412: goto fast_412;
        case 413: goto fast_413;
        case 414: goto fast_414;
        case 415: goto fast_415;
        case 416: goto fast_416;
        case 417: goto fast_417;
        case 418: goto fast_418;
        case 419: goto fast_419;
        case 420: goto fast_420;
        case 421: goto fast_421;
        case 422: goto fast_422;
        case 423: goto fast_423;
        case 424: goto fast_424;
        case 425: goto fast_425;
        case 426: goto fast_426;
        case 427: goto fast_427;
        case 428: goto fast_428;
        case 429: goto fast_429;
        case 430: goto fast_430;
        case 431: goto fast_431;
        case 432: goto fast_432;
        case 433: goto fast_433;
        case 434: goto fast_434;
        case 435: goto fast_435;
        case 436: goto fast_436;
        case 437: goto fast_437;
        case 438: goto fast_438;
        case 439: goto fast_439;
        case 440: goto fast_440;
        case 441: goto fast_441;
        case 442: goto fast_442;
        case 443: goto fast_443;
        case 444: goto fast_444;
        case 445: goto fast_445;
        case 446: goto fast_446;
        case 447: goto fast_447;
        case 448: goto fast_448;
        case 449: goto fast_449;
        case 450: goto fast_450;
        case 451: goto fast_451;
        case 452: goto fast_452;
        case 453: goto fast_453;
        case 454: goto fast_454;
        case 455: goto fast_455;
        case 456: goto fast_456;
        case 457: goto fast_457;
        case 458: goto fast_458;
        case 459: goto fast_459;
        case 460: goto fast_460;
        case 461: goto fast_461;
        case 462: goto fast_462;
        case 463: goto fast_463;
        case 464: goto fast_464;
        case 465: goto fast_465;
        case 466: goto fast_466;
        case 467: goto fast_467;
        case 468: goto fast_468;
        case 469: goto fast_469;
        case 470: goto fast_470;
        case 471: goto fast_471;
        case 472: goto fast_472;
        case 473: goto fast_473;
        case 474: goto fast_474;
        case 475: goto fast_475;
        case 476: goto fast_476;
        case 477: goto fast_477;
        case 478: goto fast_478;
        case 479: goto fast_479;
        case 480: goto fast_480;
        case 481: goto fast_481;
        case 482: goto fast_482;
        case 483: goto fast_483;
        case 484: goto fast_484;
        case 485: goto fast_485;
        case 486: goto fast_486;
        case 487: goto fast_487;
        case 488: goto fast_488;
        case 489: goto fast_489;
        case 490: goto fast_490;
        case 491: goto fast_491;
        case 492: goto fast_492;
        case 493: goto fast_493;
        case 494: goto fast_494;
        case 495: goto fast_495;
        case 496: goto fast_496;
        case 497: goto fast_497;
        case 498: goto fast_498;
        case 499: goto fast_499;
        case 500: goto fast_500;
        case 501: goto fast_501;
        case 502: goto fast_502;
        case 503: goto fast_503;
        case 504: goto fast_504;
        case 505: goto fast_505;
        case 506: goto fast_506;
        case 507: goto fast_507;
        case 508: goto fast_508;
        case 509: goto fast_509;
        case 510: goto fast_510;
        case 511: goto fast_511;
        case 512: goto fast_512;
        case 513: goto fast_513;
        case 514: goto fast_514;
        case 515: goto fast_515;
        case 516: goto fast_516;
        case 517: goto fast_517;
        case 518: goto fast_518;
        case 519: goto fast_519;
        case 520: goto fast_520;
        case 521: goto fast_521;
        case 522: goto fast_522;
        case 523: goto fast_523;
        case 524: goto fast_524;
        case 525: goto fast_525;
        case 526: goto fast_526;
        case 527: goto fast_527;
        case 528: goto fast_528;
        case 529: goto fast_529;
        case 530: goto fast_530;
        case 531: goto fast_531;
        case 532: goto fast_532;
        case 533: goto fast_533;
        case 534: goto fast_534;
        case 535: goto fast_535;
        case 536: goto fast_536;
        case 537: goto fast_537;
        case 538: goto fast_538;
        case 539: goto fast_539;
        case 540: goto fast_540;
        case 541: goto fast_541;
        case 542: goto fast_542;
        case 543: goto fast_543;
        case 544: goto fast_544;
        case 545: goto fast_545;
        case 546: goto fast_546;
        case 547: goto fast_547;
        case 548: goto fast_548;
        case 549: goto fast_549;
        case 550: goto fast_550;
        case 551: goto fast_551;
        case 552: goto fast_552;
        case 553: goto fast_553;
        case 554: goto fast_554;
        case 555: goto fast_555;
        case 556: goto fast_556;
        case 557: goto fast_557;
        case 558: goto fast_558;
        case 559: goto fast_559;
        case 560: goto fast_560;
        case 561: goto fast_561;
        case 562: goto fast_562;
        case 563: goto fast_563;
        case 564: goto fast_564;
        case 565: goto fast_565;
        case 566: goto fast_566;
        case 567: goto fast_567;
        case 568: goto fast_568;
        case 569: goto fast_569;
        case 570: goto fast_570;
        case 571: goto fast_571;
        case 572: goto fast_572;
        case 573: goto fast_573;
        case 574: goto fast_574;
        case 575: goto fast_575;
        case 576: goto fast_576;
        case 577: goto fast_577;
        case 578: goto fast_578;
        case 579: goto fast_579;
        case 580: goto fast_580;
        case 581: goto fast_581;
        case 582: goto fast_582;
        case 583: goto fast_583;
        case 584: goto fast_584;
        case 585: goto fast_585;
        case 586: goto fast_586;
        case 587: goto fast_587;
        case 588: goto fast_588;
        case 589: goto fast_589;
        case 590: goto fast_590;
        case 591: goto fast_591;
        case 592: goto fast_592;
        case 593: goto fast_593;
        case 594: goto fast_594;
        case 595: goto fast_595;
        case 596: goto fast_596;
        case 597: goto fast_597;
        case 598: goto fast_598;
        case 599: goto fast_599;
        case 600: goto fast_600;
        case 601: goto fast_601;
        case 602: goto fast_602;
        case 603: goto fast_603;
        case 604: goto fast_604;
        case 605: goto fast_605;
        case 606: goto fast_606;
        case 607: goto fast_607;
        case 608: goto fast_608;
        case 609: goto fast_609;
        case 610: goto fast_610;
        case 611: goto fast_611;
        case 612: goto fast_612;
        case 613: goto fast_613;
        case 614: goto fast_614;
        case 615: goto fast_615;
        case 616: goto fast_616;
        case 617: goto fast_617;
        case 618: goto fast_618;
        case 619: goto fast_619;
        case 620: goto fast_620;
        case 621: goto fast_621;
        case 622: goto fast_622;
        case 623: goto fast_623;
        case 624: goto fast_624;
        case 625: goto fast_625;
        case 626: goto fast_626;
        case 627: goto fast_627;
        case 628: goto fast_628;
        case 629: goto fast_629;
        case 630: goto fast_630;
        case 631: goto fast_631;
        case 632: goto fast_632;
        case 633: goto fast_633;
        case 634: goto fast_634;
        case 635: goto fast_635;
        case 636: goto fast_636;
        case 637: goto fast_637;
        case 638: goto fast_638;
        case 639: goto fast_639;
        case 640: goto fast_640;
        case 641: goto fast_641;
        case 642: goto fast_642;
        case 643: goto fast_643;
        case 644: goto fast_644;
        case 645: goto fast_645;
        case 646: goto fast_646;
        case 647: goto fast_647;
        case 648: goto fast_648;
        case 649: goto fast_649;
        case 650: goto fast_650;
        case 651: goto fast_651;
        case 652: goto fast_652;
        case 653: goto fast_653;
        case 654: goto fast_654;
        case 655: goto fast_655;
        case 656: goto fast_656;
        case 657: goto fast_657;
        case 658: goto fast_658;
        case 659: goto fast_659;
        case 660: goto fast_660;
        case 661: goto fast_661;
        case 662: goto fast_662;
        case 663: goto fast_663;
        case 664: goto fast_664;
        case 665: goto fast_665;
        case 666: goto fast_666;
        case 667: goto fast_667;
        case 668: goto fast_668;
        case 669: goto fast_669;
        case 670: goto fast_670;
        case 671: goto fast_671;
        case 672: goto fast_672;
        case 673: goto fast_673;
        case 674: goto fast_674;
        case 675: goto fast_675;
        case 676: goto fast_676;
        case 677: goto fast_677;
        case 678: goto fast_678;
        case 679: goto fast_679;
        case 680: goto fast_680;
        case 681: goto fast_681;
        case 682: goto fast_682;
        case 683: goto fast_683;
        case 684: goto fast_684;
        case 685: goto fast_685;
        case 686: goto fast_686;
        case 687: goto fast_687;
        case 688: goto fast_688;
        case 689: goto fast_689;
        case 690: goto fast_690;
        case 691: goto fast_691;
        case 692: goto fast_692;
        case 693: goto fast_693;
        case 694: goto fast_694;
        case 695: goto fast_695;
        case 696: goto fast_696;
        case 697: goto fast_697;
        case 698: goto fast_698;
        case 699: goto fast_699;
        case 700: goto fast_700;
        case 701: goto fast_701;
        case 702: goto fast_702;
        case 703: goto fast_703;
        case 704: goto fast_704;
        case 705: goto fast_705;
        case 706: goto fast_706;
        case 707: goto fast_707;
        case 708: goto fast_708;
        case 709: goto fast_709;
        case 710: goto fast_710;
        case 711: goto fast_711;
        case 712: goto fast_712;
        case 713: goto fast_713;
        case 714: goto fast_714;
        case 715: goto fast_715;
        case 716: goto fast_716;
        case 717: goto fast_717;
        case 718: goto fast_718;
        case 719: goto fast_719;
        case 720: goto fast_720;
        case 721: goto fast_721;
        case 722: goto fast_722;
        case 723: goto fast_723;
        case 724: goto fast_724;
        case 725: goto fast_725;
        case 726: goto fast_726;
        case 727: goto fast_727;
        case 728: goto fast_728;
        case 729: goto fast_729;
        case 730: goto fast_730;
        case 731: goto fast_731;
        case 732: goto fast_732;
        case 733: goto fast_733;
        case 734: goto fast_734;
        case 735: goto fast_735;
        case 736: goto fast_736;
        case 737: goto fast_737;
        case 738: goto fast_738;
        case 739: goto fast_739;
        case 740: goto fast_740;
        case 741: goto fast_741;
        case 742: goto fast_742;
        case 743: goto fast_743;
        case 744: goto fast_744;
        case 745: goto fast_745;
        case 746: goto fast_746;
        case 747: goto fast_747;
        case 748: goto fast_748;
        case 749: goto fast_749;
        case 750: goto fast_750;
        case 751: goto fast_751;
        case 752: goto fast_752;
        case 753: goto fast_753;
        case 754: goto fast_754;
        case 755: goto fast_755;
        case 756: goto fast_756;
        case 757: goto fast_757;
        case 758: goto fast_758;
        case 759: goto fast_759;
        case 760: goto fast_760;
        case 761: goto fast_761;
        case 762: goto fast_762;
        case 763: goto fast_763;
        case 764: goto fast_764;
        case 765: goto fast_765;
        case 766: goto fast_766;
        case 767: goto fast_767;
        case 768: goto fast_768;
        case 769: goto fast_769;
        case 770: goto fast_770;
        case 771: goto fast_771;
        case 772: goto fast_772;
        case 773: goto fast_773;
        case 774: goto fast_774;
        case 775: goto fast_775;
        case 776: goto fast_776;
        case 777: goto fast_777;
        case 778: goto fast_778;
        case 779: goto fast_779;
        case 780: goto fast_780;
        case 781: goto fast_781;
        case 782: goto fast_782;
        case 783: goto fast_783;
        case 784: goto fast_784;
        case 785: goto fast_785;
        case 786: goto fast_786;
        case 787: goto fast_787;
        case 788: goto fast_788;
        case 789: goto fast_789;
        case 790: goto fast_790;
        case 791: goto fast_791;
        case 792: goto fast_792;
        case 793: goto fast_793;
        case 794: goto fast_794;
        case 795: goto fast_795;
        case 796: goto fast_796;
        case 797: goto fast_797;
        case 798: goto fast_798;
        case 799: goto fast_799;
        case 800: goto fast_800;
        case 801: goto fast_801;
        case 802: goto fast_802;
        case 803: goto fast_803;
        case 804: goto fast_804;
        case 805: goto fast_805;
        case 806: goto fast_806;
        case 807: goto fast_807;
        case 808: goto fast_808;
        case 809: goto fast_809;
        case 810: goto fast_810;
        case 811: goto fast_811;
        case 812: goto fast_812;
        case 813: goto fast_813;
        case 814: goto fast_814;
        case 815: goto fast_815;
        case 816: goto fast_816;
        case 817: goto fast_817;
        case 818: goto fast_818;
        case 819: goto fast_819;
        case 820: goto fast_820;
        case 821: goto fast_821;
        case 822: goto fast_822;
        case 823: goto fast_823;
        case 824: goto fast_824;
        case 825: goto fast_825;
        case 826: goto fast_826;
        case 827: goto fast_827;
        case 828: goto fast_828;
        case 829: goto fast_829;
        case 830: goto fast_830;
        case 831: goto fast_831;
        case 832: goto fast_832;
        case 833: goto fast_833;
        case 834: goto fast_834;
        case 835: goto fast_835;
        case 836: goto fast_836;
        case 837: goto fast_837;
        case 838: goto fast_838;
        case 839: goto fast_839;
        case 840: goto fast_840;
        case 841: goto fast_841;
        case 842: goto fast_842;
        case 843: goto fast_843;
        case 844: goto fast_844;
        case 845: goto fast_845;
        case 846: goto fast_846;
        case 847: goto fast_847;
        case 848: goto fast_848;
        case 849: goto fast_849;
        case 850: goto fast_850;
        case 851: goto fast_851;
        case 852: goto fast_852;
        case 853: goto fast_853;
        case 854: goto fast_854;
        case 855: goto fast_855;
        case 856: goto fast_856;
        case 857: goto fast_857;
        case 858: goto fast_858;
        case 859: goto fast_859;
        case 860: goto fast_860;
        case 861: goto fast_861;
        case 862: goto fast_862;
        case 863: goto fast_863;
        case 864: goto fast_864;
        case 865: goto fast_865;
        case 866: goto fast_866;
        case 867: goto fast_867;
        case 868: goto fast_868;
        case 869: goto fast_869;
        case 870: goto fast_870;
        case 871: goto fast_871;
        case 872: goto fast_872;
        case 873: goto fast_873;
        case 874: goto fast_874;
        case 875: goto fast_875;
        case 876: goto fast_876;
        case 877: goto fast_877;
        case 878: goto fast_878;
        case 879: goto fast_879;
        case 880: goto fast_880;
        case 881: goto fast_881;
        case 882: goto fast_882;
        case 883: goto fast_883;
        case 884: goto fast_884;
        case 885: goto fast_885;
        case 886: goto fast_886;
        case 887: goto fast_887;
        case 888: goto fast_888;
        case 889: goto fast_889;
        case 890: goto fast_890;
        case 891: goto fast_891;
        case 892: goto fast_892;
        case 893: goto fast_893;
        case 894: goto fast_894;
        case 895: goto fast_895;
        case 896: goto fast_896;
        case 897: goto fast_897;
        case 898: goto fast_898;
        case 899: goto fast_899;
        case 900: goto fast_900;
        case 901: goto fast_901;
        case 902: goto fast_902;
        case 903: goto fast_903;
        case 904: goto fast_904;
        case 905: goto fast_905;
        case 906: goto fast_906;
        case 907: goto fast_907;
        case 908: goto fast_908;
        case 909: goto fast_909;
        case 910: goto fast_910;
        case 911: goto fast_911;
        case 912: goto fast_912;
        case 913: goto fast_913;
        case 914: goto fast_914;
        case 915: goto fast_915;
        case 916: goto fast_916;
        case 917: goto fast_917;
        case 918: goto fast_918;
        case 919: goto fast_919;
        case 920: goto fast_920;
        case 921: goto fast_921;
        case 922: goto fast_922;
        case 923: goto fast_923;
        case 924: goto fast_924;
        case 925: goto fast_925;
        case 926: goto fast_926;
        case 927: goto fast_927;
        case 928: goto fast_928;
        case 929: goto fast_929;
        case 930: goto fast_930;
        case 931: goto fast_931;
        case 932: goto fast_932;
        case 933: goto fast_933;
        case 934: goto fast_934;
        case 935: goto fast_935;
        case 936: goto fast_936;
        case 937: goto fast_937;
        case 938: goto fast_938;
        case 939: goto fast_939;
        case 940: goto fast_940;
        case 941: goto fast_941;
        case 942: goto fast_942;
        case 943: goto fast_943;
        case 944: goto fast_944;
        case 945: goto fast_945;
        case 946: goto fast_946;
        case 947: goto fast_947;
        case 948: goto fast_948;
        case 949: goto fast_949;
        case 950: goto fast_950;
        case 951: goto fast_951;
        case 952: goto fast_952;
        case 953: goto fast_953;
        case 954: goto fast_954;
        case 955: goto fast_955;
        case 956: goto fast_956;
        case 957: goto fast_957;
        case 958: goto fast_958;
        case 959: goto fast_959;
        case 960: goto fast_960;
        case 961: goto fast_961;
        case 962: goto fast_962;
        case 963: goto fast_963;
        case 964: goto fast_964;
        case 965: goto fast_965;
        case 966: goto fast_966;
        case 967: goto fast_967;
        case 968: goto fast_968;
        case 969: goto fast_969;
        case 970: goto fast_970;
        case 971: goto fast_971;
        case 972: goto fast_972;
        case 973: goto fast_973;
        case 974: goto fast_974;
        case 975: goto fast_975;
        case 976: goto fast_976;
        case 977: goto fast_977;
        case 978: goto fast_978;
        case 979: goto fast_979;
        case 980: goto fast_980;
        case 981: goto fast_981;
        case 982: goto fast_982;
        case 983: goto fast_983;
        case 984: goto fast_984;
        case 985: goto fast_985;
        case 986: goto fast_986;
        case 987: goto fast_987;
        case 988: goto fast_988;
        case 989: goto fast_989;
        case 990: goto fast_990;
        case 991: goto fast_991;
        case 992: goto fast_992;
        case 993: goto fast_993;
        case 994: goto fast_994;
        case 995: goto fast_995;
        case 996: goto fast_996;
        case 997: goto fast_997;
        case 998: goto fast_998;
        case 999: goto fast_999;
        case 1000: goto fast_1000;
        case 1001: goto fast_1001;
        case 1002: goto fast_1002;
        case 1003: goto fast_1003;
        case 1004: goto fast_1004;
        case 1005: goto fast_1005;
        case 1006: goto fast_1006;
        case 1007: goto fast_1007;
        case 1008: goto fast_1008;
        case 1009: goto fast_1009;
        case 1010: goto fast_1010;
        case 1011: goto fast_1011;
        case 1012: goto fast_1012;
        case 1013: goto fast_1013;
        case 1014: goto fast_1014;
        case 1015: goto fast_1015;
        case 1016: goto fast_1016;
        case 1017: goto fast_1017;
        case 1018: goto fast_1018;
        case 1019: goto fast_1019;
        case 1020: goto fast_1020;
        case 1021: goto fast_1021;
        case 1022: goto fast_1022;
        case 1023: goto fast_1023;
        case 1024: goto fast_1024;
        case 1025: goto fast_1025;
        case 1026: goto fast_1026;
        case 1027: goto fast_1027;
        case 1028: goto fast_1028;
        case 1029: goto fast_1029;
        case 1030: goto fast_1030;
        case 1031: goto fast_1031;
        case 1032: goto fast_1032;
        case 1033: goto fast_1033;
        case 1034: goto fast_1034;
        case 1035: goto fast_1035;
        case 1036: goto fast_1036;
        case 1037: goto fast_1037;
        case 1038: goto fast_1038;
        case 1039: goto fast_1039;
        case 1040: goto fast_1040;
        case 1041: goto fast_1041;
        case 1042: goto fast_1042;
        case 1043: goto fast_1043;
        case 1044: goto fast_1044;
        case 1045: goto fast_1045;
        case 1046: goto fast_1046;
        case 1047: goto fast_1047;
        case 1048: goto fast_1048;
        case 1049: goto fast_1049;
        case 1050: goto fast_1050;
        case 1051: goto fast_1051;
        case 1052: goto fast_1052;
        case 1053: goto fast_1053;
        case 1054: goto fast_1054;
        case 1055: goto fast_1055;
        case 1056: goto fast_1056;
        case 1057: goto fast_1057;
        case 1058: goto fast_1058;
        case 1059: goto fast_1059;
        case 1060: goto fast_1060;
        case 1061: goto fast_1061;
        case 1062: goto fast_1062;
        case 1063: goto fast_1063;
        case 1064: goto fast_1064;
        case 1065: goto fast_1065;
        case 1066: goto fast_1066;
        case 1067: goto fast_1067;
        case 1068: goto fast_1068;
        case 1069: goto fast_1069;
        case 1070: goto fast_1070;
        case 1071: goto fast_1071;
        case 1072: goto fast_1072;
        case 1073: goto fast_1073;
        case 1074: goto fast_1074;
        case 1075: goto fast_1075;
        case 1076: goto fast_1076;
        case 1077: goto fast_1077;
        case 1078: goto fast_1078;
        case 1079: goto fast_1079;
        case 1080: goto fast_1080;
        case 1081: goto fast_1081;
        case 1082: goto fast_1082;
        case 1083: goto fast_1083;
        case 1084: goto fast_1084;
        case 1085: goto fast_1085;
        case 1086: goto fast_1086;
        case 1087: goto fast_1087;
        case 1088: goto fast_1088;
        case 1089: goto fast_1089;
        case 1090: goto fast_1090;
        case 1091: goto fast_1091;
        case 1092: goto fast_1092;
        case 1093: goto fast_1093;
        case 1094: goto fast_1094;
        case 1095: goto fast_1095;
        case 1096: goto fast_1096;
        case 1097: goto fast_1097;
        case 1098: goto fast_1098;
        case 1099: goto fast_1099;
        case 1100: goto fast_1100;
        case 1101: goto fast_1101;
        case 1102: goto fast_1102;
        case 1103: goto fast_1103;
        case 1104: goto fast_1104;
        case 1105: goto fast_1105;
        case 1106: goto fast_1106;
        case 1107: goto fast_1107;
        case 1108: goto fast_1108;
        case 1109: goto fast_1109;
        case 1110: goto fast_1110;
        case 1111: goto fast_1111;
        case 1112: goto fast_1112;
        case 1113: goto fast_1113;
        case 1114: goto fast_1114;
        case 1115: goto fast_1115;
        case 1116: goto fast_1116;
        case 1117: goto fast_1117;
        case 1118: goto fast_1118;
        case 1119: goto fast_1119;
        case 1120: goto fast_1120;
        case 1121: goto fast_1121;
        case 1122: goto fast_1122;
        case 1123: goto fast_1123;
        case 1124: goto fast_1124;
        case 1125: goto fast_1125;
        case 1126: goto fast_1126;
        case 1127: goto fast_1127;
        case 1128: goto fast_1128;
        case 1129: goto fast_1129;
        case 1130: goto fast_1130;
        case 1131: goto fast_1131;
        case 1132: goto fast_1132;
        case 1133: goto fast_1133;
        case 1134: goto fast_1134;
        case 1135: goto fast_1135;
        case 1136: goto fast_1136;
        case 1137: goto fast_1137;
        case 1138: goto fast_1138;
        case 1139: goto fast_1139;
        case 1140: goto fast_1140;
        case 1141: goto fast_1141;
        case 1142: goto fast_1142;
        case 1143: goto fast_1143;
        case 1144: goto fast_1144;
        case 1145: goto fast_1145;
        case 1146: goto fast_1146;
        case 1147: goto fast_1147;
        case 1148: goto fast_1148;
        case 1149: goto fast_1149;
        case 1150: goto fast_1150;
        case 1151: goto fast_1151;
        case 1152: goto fast_1152;
        case 1153: goto fast_1153;
        case 1154: goto fast_1154;
        case 1155: goto fast_1155;
        case 1156: goto fast_1156;
        case 1157: goto fast_1157;
        case 1158: goto fast_1158;
        case 1159: goto fast_1159;
        case 1160: goto fast_1160;
        case 1161: goto fast_1161;
        case 1162: goto fast_1162;
        case 1163: goto fast_1163;
        case 1164: goto fast_1164;
        case 1165: goto fast_1165;
        case 1166: goto fast_1166;
        case 1167: goto fast_1167;
        case 1168: goto fast_1168;
        case 1169: goto fast_1169;
        case 1170: goto fast_1170;
        case 1171: goto fast_1171;
        case 1172: goto fast_1172;
        case 1173: goto fast_1173;
        case 1174: goto fast_1174;
        case 1175: goto fast_1175;
        case 1176: goto fast_1176;
        case 1177: goto fast_1177;
        case 1178: goto fast_1178;
        case 1179: goto fast_1179;
        case 1180: goto fast_1180;
        case 1181: goto fast_1181;
        case 1182: goto fast_1182;
        case 1183: goto fast_1183;
        case 1184: goto fast_1184;
        case 1185: goto fast_1185;
        case 1186: goto fast_1186;
        case 1187: goto fast_1187;
        case 1188: goto fast_1188;
        case 1189: goto fast_1189;
        case 1190: goto fast_1190;
        case 1191: goto fast_1191;
        case 1192: goto fast_1192;
        case 1193: goto fast_1193;
        case 1194: goto fast_1194;
        case 1195: goto fast_1195;
        case 1196: goto fast_1196;
        case 1197: goto fast_1197;
        case 1198: goto fast_1198;
        case 1199: goto fast_1199;
        case 1200: goto fast_1200;
        case 1201: goto fast_1201;
        case 1202: goto fast_1202;
        case 1203: goto fast_1203;
        case 1204: goto fast_1204;
        case 1205: goto fast_1205;
        case 1206: goto fast_1206;
        case 1207: goto fast_1207;
        case 1208: goto fast_1208;
        case 1209: goto fast_1209;
        case 1210: goto fast_1210;
        case 1211: goto fast_1211;
        case 1212: goto fast_1212;
        case 1213: goto fast_1213;
        case 1214: goto fast_1214;
        case 1215: goto fast_1215;
        case 1216: goto fast_1216;
        case 1217: goto fast_1217;
        case 1218: goto fast_1218;
        case 1219: goto fast_1219;
        case 1220: goto fast_1220;
        case 1221: goto fast_1221;
        case 1222: goto fast_1222;
        case 1223: goto fast_1223;
        case 1224: goto fast_1224;
        case 1225: goto fast_1225;
        case 1226: goto fast_1226;
        case 1227: goto fast_1227;
        case 1228: goto fast_1228;
        case 1229: goto fast_1229;
        case 1230: goto fast_1230;
        case 1231: goto fast_1231;
        case 1232: goto fast_1232;
        case 1233: goto fast_1233;
        case 1234: goto fast_1234;
        case 1235: goto fast_1235;
        case 1236: goto fast_1236;
        case 1237: goto fast_1237;
        case 1238: goto fast_1238;
        case 1239: goto fast_1239;
        case 1240: goto fast_1240;
        case 1241: goto fast_1241;
        case 1242: goto fast_1242;
        case 1243: goto fast_1243;
        case 1244: goto fast_1244;
        case 1245: goto fast_1245;
        case 1246: goto fast_1246;
        case 1247: goto fast_1247;
        case 1248: goto fast_1248;
        case 1249: goto fast_1249;
        case 1250: goto fast_1250;
        case 1251: goto fast_1251;
        case 1252: goto fast_1252;
        case 1253: goto fast_1253;
        case 1254: goto fast_1254;
        case 1255: goto fast_1255;
        case 1256: goto fast_1256;
        case 1257: goto fast_1257;
        case 1258: goto fast_1258;
        case 1259: goto fast_1259;
        case 1260: goto fast_1260;
        case 1261: goto fast_1261;
        case 1262: goto fast_1262;
        case 1263: goto fast_1263;
        case 1264: goto fast_1264;
        case 1265: goto fast_1265;
        case 1266: goto fast_1266;
        case 1267: goto fast_1267;
        case 1268: goto fast_1268;
        case 1269: goto fast_1269;
        case 1270: goto fast_1270;
        case 1271: goto fast_1271;
        case 1272: goto fast_1272;
        case 1273: goto fast_1273;
        case 1274: goto fast_1274;
        case 1275: goto fast_1275;
        case 1276: goto fast_1276;
        case 1277: goto fast_1277;
        case 1278: goto fast_1278;
        case 1279: goto fast_1279;
        case 1280: goto fast_1280;
        case 1281: goto fast_1281;
        case 1282: goto fast_1282;
        case 1283: goto fast_1283;
        case 1284: goto fast_1284;
        case 1285: goto fast_1285;
        case 1286: goto fast_1286;
        case 1287: goto fast_1287;
        case 1288: goto fast_1288;
        case 1289: goto fast_1289;
        case 1290: goto fast_1290;
        case 1291: goto fast_1291;
        case 1292: goto fast_1292;
        case 1293: goto fast_1293;
        case 1294: goto fast_1294;
        case 1295: goto fast_1295;
        case 1296: goto fast_1296;
        case 1297: goto fast_1297;
        case 1298: goto fast_1298;
        case 1299: goto fast_1299;
        case 1300: goto fast_1300;
        case 1301: goto fast_1301;
        case 1302: goto fast_1302;
        case 1303: goto fast_1303;
        case 1304: goto fast_1304;
        case 1305: goto fast_1305;
        case 1306: goto fast_1306;
        case 1307: goto fast_1307;
        case 1308: goto fast_1308;
        case 1309: goto fast_1309;
        case 1310: goto fast_1310;
        case 1311: goto fast_1311;
        case 1312: goto fast_1312;
        case 1313: goto fast_1313;
        case 1314: goto fast_1314;
        case 1315: goto fast_1315;
        case 1316: goto fast_1316;
        case 1317: goto fast_1317;
        case 1318: goto fast_1318;
        case 1319: goto fast_1319;
        case 1320: goto fast_1320;
        case 1321: goto fast_1321;
        case 1322: goto fast_1322;
        case 1323: goto fast_1323;
        case 1324: goto fast_1324;
        case 1325: goto fast_1325;
        case 1326: goto fast_1326;
        case 1327: goto fast_1327;
        case 1328: goto fast_1328;
        case 1329: goto fast_1329;
        case 1330: goto fast_1330;
        case 1331: goto fast_1331;
        case 1332: goto fast_1332;
        case 1333: goto fast_1333;
        case 1334: goto fast_1334;
        case 1335: goto fast_1335;
        case 1336: goto fast_1336;
        case 1337: goto fast_1337;
        case 1338: goto fast_1338;
        case 1339: goto fast_1339;
        case 1340: goto fast_1340;
        case 1341: goto fast_1341;
        case 1342: goto fast_1342;
        case 1343: goto fast_1343;
        case 1344: goto fast_1344;
        case 1345: goto fast_1345;
        case 1346: goto fast_1346;
        case 1347: goto fast_1347;
        case 1348: goto fast_1348;
        case 1349: goto fast_1349;
        case 1350: goto fast_1350;
        case 1351: goto fast_1351;
        case 1352: goto fast_1352;
        case 1353: goto fast_1353;
        case 1354: goto fast_1354;
        case 1355: goto fast_1355;
        case 1356: goto fast_1356;
        case 1357: goto fast_1357;
        case 1358: goto fast_1358;
        case 1359: goto fast_1359;
        case 1360: goto fast_1360;
        case 1361: goto fast_1361;
        case 1362: goto fast_1362;
        case 1363: goto fast_1363;
        case 1364: goto fast_1364;
        case 1365: goto fast_1365;
        case 1366: goto fast_1366;
        case 1367: goto fast_1367;
        case 1368: goto fast_1368;
        case 1369: goto fast_1369;
        case 1370: goto fast_1370;
        case 1371: goto fast_1371;
        case 1372: goto fast_1372;
        case 1373: goto fast_1373;
        case 1374: goto fast_1374;
        case 1375: goto fast_1375;
        case 1376: goto fast_1376;
        case 1377: goto fast_1377;
        case 1378: goto fast_1378;
        case 1379: goto fast_1379;
        case 1380: goto fast_1380;
        case 1381: goto fast_1381;
        case 1382: goto fast_1382;
        case 1383: goto fast_1383;
        case 1384: goto fast_1384;
        case 1385: goto fast_1385;
        case 1386: goto fast_1386;
        case 1387: goto fast_1387;
        case 1388: goto fast_1388;
        case 1389: goto fast_1389;
        case 1390: goto fast_1390;
        case 1391: goto fast_1391;
        case 1392: goto fast_1392;
        case 1393: goto fast_1393;
        case 1394: goto fast_1394;
        case 1395: goto fast_1395;
        case 1396: goto fast_1396;
        case 1397: goto fast_1397;
        case 1398: goto fast_1398;
        case 1399: goto fast_1399;
        case 1400: goto fast_1400;
        case 1401: goto fast_1401;
        case 1402: goto fast_1402;
        case 1403: goto fast_1403;
        case 1404: goto fast_1404;
        case 1405: goto fast_1405;
        case 1406: goto fast_1406;
        case 1407: goto fast_1407;
        case 1408: goto fast_1408;
        case 1409: goto fast_1409;
        case 1410: goto fast_1410;
        case 1411: goto fast_1411;
        case 1412: goto fast_1412;
        case 1413: goto fast_1413;
        case 1414: goto fast_1414;
        case 1415: goto fast_1415;
        case 1416: goto fast_1416;
        case 1417: goto fast_1417;
        case 1418: goto fast_1418;
        case 1419: goto fast_1419;
        case 1420: goto fast_1420;
        case 1421: goto fast_1421;
        case 1422: goto fast_1422;
        case 1423: goto fast_1423;
        case 1424: goto fast_1424;
        case 1425: goto fast_1425;
        case 1426: goto fast_1426;
        case 1427: goto fast_1427;
        case 1428: goto fast_1428;
        case 1429: goto fast_1429;
        case 1430: goto fast_1430;
        case 1431: goto fast_1431;
        case 1432: goto fast_1432;
        case 1433: goto fast_1433;
        case 1434: goto fast_1434;
        case 1435: goto fast_1435;
        case 1436: goto fast_1436;
        case 1437: goto fast_1437;
        case 1438: goto fast_1438;
        case 1439: goto fast_1439;
        case 1440: goto fast_1440;
        case 1441: goto fast_1441;
        case 1442: goto fast_1442;
        case 1443: goto fast_1443;
        case 1444: goto fast_1444;
        case 1445: goto fast_1445;
        case 1446: goto fast_1446;
        case 1447: goto fast_1447;
        case 1448: goto fast_1448;
        case 1449: goto fast_1449;
        case 1450: goto fast_1450;
        case 1451: goto fast_1451;
        case 1452: goto fast_1452;
        case 1453: goto fast_1453;
        case 1454: goto fast_1454;
        case 1455: goto fast_1455;
        case 1456: goto fast_1456;
        case 1457: goto fast_1457;
        case 1458: goto fast_1458;
        case 1459: goto fast_1459;
        case 1460: goto fast_1460;
        case 1461: goto fast_1461;
        case 1462: goto fast_1462;
        case 1463: goto fast_1463;
        case 1464: goto fast_1464;
        case 1465: goto fast_1465;
        case 1466: goto fast_1466;
        case 1467: goto fast_1467;
        case 1468: goto fast_1468;
        case 1469: goto fast_1469;
        case 1470: goto fast_1470;
        case 1471: goto fast_1471;
        case 1472: goto fast_1472;
        case 1473: goto fast_1473;
        case 1474: goto fast_1474;
        case 1475: goto fast_1475;
        case 1476: goto fast_1476;
        case 1477: goto fast_1477;
        case 1478: goto fast_1478;
        case 1479: goto fast_1479;
        case 1480: goto fast_1480;
        case 1481: goto fast_1481;
        case 1482: goto fast_1482;
        case 1483: goto fast_1483;
        case 1484: goto fast_1484;
        case 1485: goto fast_1485;
        case 1486: goto fast_1486;
        case 1487: goto fast_1487;
        case 1488: goto fast_1488;
        case 1489: goto fast_1489;
        case 1490: goto fast_1490;
        case 1491: goto fast_1491;
        case 1492: goto fast_1492;
        case 1493: goto fast_1493;
        case 1494: goto fast_1494;
        case 1495: goto fast_1495;
        case 1496: goto fast_1496;
        case 1497: goto fast_1497;
        case 1498: goto fast_1498;
        case 1499: goto fast_1499;
        case 1500: goto fast_1500;
        case 1501: goto fast_1501;
        case 1502: goto fast_1502;
        case 1503: goto fast_1503;
        case 1504: goto fast_1504;
        case 1505: goto fast_1505;
        case 1506: goto fast_1506;
        case 1507: goto fast_1507;
        case 1508: goto fast_1508;
        case 1509: goto fast_1509;
        case 1510: goto fast_1510;
        case 1511: goto fast_1511;
        case 1512: goto fast_1512;
        case 1513: goto fast_1513;
        case 1514: goto fast_1514;
        case 1515: goto fast_1515;
        case 1516: goto fast_1516;
        case 1517: goto fast_1517;
        case 1518: goto fast_1518;
        case 1519: goto fast_1519;
        case 1520: goto fast_1520;
        case 1521: goto fast_1521;
        case 1522: goto fast_1522;
        case 1523: goto fast_1523;
        case 1524: goto fast_1524;
        case 1525: goto fast_1525;
        case 1526: goto fast_1526;
        case 1527: goto fast_1527;
        case 1528: goto fast_1528;
        case 1529: goto fast_1529;
        case 1530: goto fast_1530;
        case 1531: goto fast_1531;
        case 1532: goto fast_1532;
        case 1533: goto fast_1533;
        case 1534: goto fast_1534;
        case 1535: goto fast_1535;
        case 1536: goto fast_1536;
        case 1537: goto fast_1537;
        case 1538: goto fast_1538;
        case 1539: goto fast_1539;
        case 1540: goto fast_1540;
        case 1541: goto fast_1541;
        case 1542: goto fast_1542;
        case 1543: goto fast_1543;
        case 1544: goto fast_1544;
        case 1545: goto fast_1545;
        case 1546: goto fast_1546;
        case 1547: goto fast_1547;
        case 1548: goto fast_1548;
        case 1549: goto fast_1549;
        case 1550: goto fast_1550;
        case 1551: goto fast_1551;
        case 1552: goto fast_1552;
        case 1553: goto fast_1553;
        case 1554: goto fast_1554;
        case 1555: goto fast_1555;
        case 1556: goto fast_1556;
        case 1557: goto fast_1557;
        case 1558: goto fast_1558;
        case 1559: goto fast_1559;
        case 1560: goto fast_1560;
        case 1561: goto fast_1561;
        case 1562: goto fast_1562;
        case 1563: goto fast_1563;
        case 1564: goto fast_1564;
        case 1565: goto fast_1565;
        case 1566: goto fast_1566;
        case 1567: goto fast_1567;
        case 1568: goto fast_1568;
        case 1569: goto fast_1569;
        case 1570: goto fast_1570;
        case 1571: goto fast_1571;
        case 1572: goto fast_1572;
        case 1573: goto fast_1573;
        case 1574: goto fast_1574;
        case 1575: goto fast_1575;
        case 1576: goto fast_1576;
        case 1577: goto fast_1577;
        case 1578: goto fast_1578;
        case 1579: goto fast_1579;
        case 1580: goto fast_1580;
        case 1581: goto fast_1581;
        case 1582: goto fast_1582;
        case 1583: goto fast_1583;
        case 1584: goto fast_1584;
        case 1585: goto fast_1585;
        case 1586: goto fast_1586;
        case 1587: goto fast_1587;
        case 1588: goto fast_1588;
        case 1589: goto fast_1589;
        case 1590: goto fast_1590;
        case 1591: goto fast_1591;
        case 1592: goto fast_1592;
        case 1593: goto fast_1593;
        case 1594: goto fast_1594;
        case 1595: goto fast_1595;
        case 1596: goto fast_1596;
        case 1597: goto fast_1597;
        case 1598: goto fast_1598;
        case 1599: goto fast_1599;
        case 1600: goto fast_1600;
        case 1601: goto fast_1601;
        case 1602: goto fast_1602;
        case 1603: goto fast_1603;
        case 1604: goto fast_1604;
        case 1605: goto fast_1605;
        case 1606: goto fast_1606;
        case 1607: goto fast_1607;
        case 1608: goto fast_1608;
        case 1609: goto fast_1609;
        case 1610: goto fast_1610;
        case 1611: goto fast_1611;
        case 1612: goto fast_1612;
        case 1613: goto fast_1613;
        case 1614: goto fast_1614;
        case 1615: goto fast_1615;
        case 1616: goto fast_1616;
        case 1617: goto fast_1617;
        case 1618: goto fast_1618;
        case 1619: goto fast_1619;
        case 1620: goto fast_1620;
        case 1621: goto fast_1621;
        case 1622: goto fast_1622;
        case 1623: goto fast_1623;
        case 1624: goto fast_1624;
        case 1625: goto fast_1625;
        case 1626: goto fast_1626;
        case 1627: goto fast_1627;
        case 1628: goto fast_1628;
        case 1629: goto fast_1629;
        case 1630: goto fast_1630;
        case 1631: goto fast_1631;
        case 1632: goto fast_1632;
        case 1633: goto fast_1633;
        case 1634: goto fast_1634;
        case 1635: goto fast_1635;
        case 1636: goto fast_1636;
        case 1637: goto fast_1637;
        case 1638: goto fast_1638;
        case 1639: goto fast_1639;
        case 1640: goto fast_1640;
        case 1641: goto fast_1641;
        case 1642: goto fast_1642;
        case 1643: goto fast_1643;
        case 1644: goto fast_1644;
        case 1645: goto fast_1645;
        case 1646: goto fast_1646;
        case 1647: goto fast_1647;
        case 1648: goto fast_1648;
        case 1649: goto fast_1649;
        case 1650: goto fast_1650;
        case 1651: goto fast_1651;
        case 1652: goto fast_1652;
        case 1653: goto fast_1653;
        case 1654: goto fast_1654;
        case 1655: goto fast_1655;
        case 1656: goto fast_1656;
        case 1657: goto fast_1657;
        case 1658: goto fast_1658;
        case 1659: goto fast_1659;
        case 1660: goto fast_1660;
        case 1661: goto fast_1661;
        case 1662: goto fast_1662;
        case 1663: goto fast_1663;
        case 1664: goto fast_1664;
        case 1665: goto fast_1665;
        case 1666: goto fast_1666;
        case 1667: goto fast_1667;
        case 1668: goto fast_1668;
        case 1669: goto fast_1669;
        case 1670: goto fast_1670;
        case 1671: goto fast_1671;
        case 1672: goto fast_1672;
        case 1673: goto fast_1673;
        case 1674: goto fast_1674;
        case 1675: goto fast_1675;
        case 1676: goto fast_1676;
        case 1677: goto fast_1677;
        case 1678: goto fast_1678;
        case 1679: goto fast_1679;
        case 1680: goto fast_1680;
        case 1681: goto fast_1681;
        case 1682: goto fast_1682;
        case 1683: goto fast_1683;
        case 1684: goto fast_1684;
        case Z80_DDFD_M1_T2: goto fast_Z80_DDFD_M1_T2;
        case Z80_DDFD_M1_T3: goto fast_Z80_DDFD_M1_T3;
        case Z80_DDFD_M1_T4: goto fast_Z80_DDFD_M1_T4;
        case Z80_DDFD_D_T1: goto fast_Z80_DDFD_D_T1;
        case Z80_DDFD_D_T2: goto fast_Z80_DDFD_D_T2;
        case Z80_DDFD_D_T3: goto fast_Z80_DDFD_D_T3;
        case Z80_DDFD_D_T4: goto fast_Z80_DDFD_D_T4;
        case Z80_DDFD_D_T5: goto fast_Z80_DDFD_D_T5;
        case Z80_DDFD_D_T6: goto fast_Z80_DDFD_D_T6;
        case Z80_DDFD_D_T7: goto fast_Z80_DDFD_D_T7;
        case Z80_DDFD_D_T8: goto fast_Z80_DDFD_D_T8;
        case Z80_DDFD_LDHLN_WR_T1: goto fast_Z80_DDFD_LDHLN_WR_T1;
        case Z80_DDFD_LDHLN_WR_T2: goto fast_Z80_DDFD_LDHLN_WR_T2;
        case Z80_DDFD_LDHLN_WR_T3: goto fast_Z80_DDFD_LDHLN_WR_T3;
        case Z80_DDFD_LDHLN_OVERLAPPED: goto fast_Z80_DDFD_LDHLN_OVERLAPPED;
        case Z80_CB_M1_T2: goto fast_Z80_CB_M1_T2;
        case Z80_CB_M1_T3: goto fast_Z80_CB_M1_T3;
        case Z80_CB_M1_T4: goto fast_Z80_CB_M1_T4;
        case Z80_ED_M1_T2: goto fast_Z80_ED_M1_T2;
        case Z80_ED_M1_T3: goto fast_Z80_ED_M1_T3;
        case Z80_ED_M1_T4: goto fast_Z80_ED_M1_T4;
        case Z80_M1_T2: goto fast_Z80_M1_T2;
        case Z80_M1_T3: goto fast_Z80_M1_T3;
        case Z80_M1_T4: goto fast_Z80_M1_T4;
        default: _Z80_UNREACHABLE;
    }
fast_0:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_0; // NOP (0)
finish_0:
    board_finish_slice(b,pins,elapsed,0); return elapsed;
fast_1:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_512; // LD BC,nn (0)
fast_2:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_518; // LD (BC),A (0)
fast_3:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->bc++;goto fast_521; // INC BC (0)
fast_4:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->b=_z80_inc8(cpu,cpu->b);pins=_z80_fetch(cpu,pins); goto finish_4; // INC B (0)
finish_4:
    board_finish_slice(b,pins,elapsed,4); return elapsed;
fast_5:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->b=_z80_dec8(cpu,cpu->b);pins=_z80_fetch(cpu,pins); goto finish_5; // DEC B (0)
finish_5:
    board_finish_slice(b,pins,elapsed,5); return elapsed;
fast_6:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_523; // LD B,n (0)
fast_7:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_rlca(cpu);pins=_z80_fetch(cpu,pins); goto finish_7; // RLCA (0)
finish_7:
    board_finish_slice(b,pins,elapsed,7); return elapsed;
fast_8:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_ex_af_af2(cpu);pins=_z80_fetch(cpu,pins); goto finish_8; // EX AF,AF' (0)
finish_8:
    board_finish_slice(b,pins,elapsed,8); return elapsed;
fast_9:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_add16(cpu,cpu->bc);goto fast_526; // ADD HL,BC (0)
fast_10:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_533; // LD A,(BC) (0)
fast_11:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->bc--;goto fast_536; // DEC BC (0)
fast_12:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->c=_z80_inc8(cpu,cpu->c);pins=_z80_fetch(cpu,pins); goto finish_12; // INC C (0)
finish_12:
    board_finish_slice(b,pins,elapsed,12); return elapsed;
fast_13:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->c=_z80_dec8(cpu,cpu->c);pins=_z80_fetch(cpu,pins); goto finish_13; // DEC C (0)
finish_13:
    board_finish_slice(b,pins,elapsed,13); return elapsed;
fast_14:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_538; // LD C,n (0)
fast_15:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_rrca(cpu);pins=_z80_fetch(cpu,pins); goto finish_15; // RRCA (0)
finish_15:
    board_finish_slice(b,pins,elapsed,15); return elapsed;
fast_16:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_541; // DJNZ d (0)
fast_17:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_550; // LD DE,nn (0)
fast_18:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_556; // LD (DE),A (0)
fast_19:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->de++;goto fast_559; // INC DE (0)
fast_20:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->d=_z80_inc8(cpu,cpu->d);pins=_z80_fetch(cpu,pins); goto finish_20; // INC D (0)
finish_20:
    board_finish_slice(b,pins,elapsed,20); return elapsed;
fast_21:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->d=_z80_dec8(cpu,cpu->d);pins=_z80_fetch(cpu,pins); goto finish_21; // DEC D (0)
finish_21:
    board_finish_slice(b,pins,elapsed,21); return elapsed;
fast_22:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_561; // LD D,n (0)
fast_23:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_rla(cpu);pins=_z80_fetch(cpu,pins); goto finish_23; // RLA (0)
finish_23:
    board_finish_slice(b,pins,elapsed,23); return elapsed;
fast_24:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_564; // JR d (0)
fast_25:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_add16(cpu,cpu->de);goto fast_572; // ADD HL,DE (0)
fast_26:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_579; // LD A,(DE) (0)
fast_27:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->de--;goto fast_582; // DEC DE (0)
fast_28:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->e=_z80_inc8(cpu,cpu->e);pins=_z80_fetch(cpu,pins); goto finish_28; // INC E (0)
finish_28:
    board_finish_slice(b,pins,elapsed,28); return elapsed;
fast_29:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->e=_z80_dec8(cpu,cpu->e);pins=_z80_fetch(cpu,pins); goto finish_29; // DEC E (0)
finish_29:
    board_finish_slice(b,pins,elapsed,29); return elapsed;
fast_30:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_584; // LD E,n (0)
fast_31:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_rra(cpu);pins=_z80_fetch(cpu,pins); goto finish_31; // RRA (0)
finish_31:
    board_finish_slice(b,pins,elapsed,31); return elapsed;
fast_32:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_587; // JR NZ,d (0)
fast_33:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_595; // LD HL,nn (0)
fast_34:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_601; // LD (nn),HL (0)
fast_35:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->hlx[cpu->hlx_idx].hl++;goto fast_613; // INC HL (0)
fast_36:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->hlx[cpu->hlx_idx].h=_z80_inc8(cpu,cpu->hlx[cpu->hlx_idx].h);pins=_z80_fetch(cpu,pins); goto finish_36; // INC H (0)
finish_36:
    board_finish_slice(b,pins,elapsed,36); return elapsed;
fast_37:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->hlx[cpu->hlx_idx].h=_z80_dec8(cpu,cpu->hlx[cpu->hlx_idx].h);pins=_z80_fetch(cpu,pins); goto finish_37; // DEC H (0)
finish_37:
    board_finish_slice(b,pins,elapsed,37); return elapsed;
fast_38:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_615; // LD H,n (0)
fast_39:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_daa(cpu);pins=_z80_fetch(cpu,pins); goto finish_39; // DAA (0)
finish_39:
    board_finish_slice(b,pins,elapsed,39); return elapsed;
fast_40:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_618; // JR Z,d (0)
fast_41:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_add16(cpu,cpu->hlx[cpu->hlx_idx].hl);goto fast_626; // ADD HL,HL (0)
fast_42:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_633; // LD HL,(nn) (0)
fast_43:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->hlx[cpu->hlx_idx].hl--;goto fast_645; // DEC HL (0)
fast_44:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->hlx[cpu->hlx_idx].l=_z80_inc8(cpu,cpu->hlx[cpu->hlx_idx].l);pins=_z80_fetch(cpu,pins); goto finish_44; // INC L (0)
finish_44:
    board_finish_slice(b,pins,elapsed,44); return elapsed;
fast_45:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->hlx[cpu->hlx_idx].l=_z80_dec8(cpu,cpu->hlx[cpu->hlx_idx].l);pins=_z80_fetch(cpu,pins); goto finish_45; // DEC L (0)
finish_45:
    board_finish_slice(b,pins,elapsed,45); return elapsed;
fast_46:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_647; // LD L,n (0)
fast_47:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_cpl(cpu);pins=_z80_fetch(cpu,pins); goto finish_47; // CPL (0)
finish_47:
    board_finish_slice(b,pins,elapsed,47); return elapsed;
fast_48:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_650; // JR NC,d (0)
fast_49:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_658; // LD SP,nn (0)
fast_50:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_664; // LD (nn),A (0)
fast_51:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->sp++;goto fast_673; // INC SP (0)
fast_52:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_675; // INC (HL) (0)
fast_53:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_682; // DEC (HL) (0)
fast_54:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_689; // LD (HL),n (0)
fast_55:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    { const uint8_t xy=((b->q^cpu->f)|cpu->a)&(Z80_YF|Z80_XF); _z80_scf(cpu); cpu->f=(cpu->f&~(Z80_YF|Z80_XF))|xy; }pins=_z80_fetch(cpu,pins); goto finish_55; // SCF (0)
finish_55:
    board_finish_slice(b,pins,elapsed,55); return elapsed;
fast_56:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_695; // JR C,d (0)
fast_57:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_add16(cpu,cpu->sp);goto fast_703; // ADD HL,SP (0)
fast_58:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_710; // LD A,(nn) (0)
fast_59:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->sp--;goto fast_719; // DEC SP (0)
fast_60:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->a=_z80_inc8(cpu,cpu->a);pins=_z80_fetch(cpu,pins); goto finish_60; // INC A (0)
finish_60:
    board_finish_slice(b,pins,elapsed,60); return elapsed;
fast_61:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->a=_z80_dec8(cpu,cpu->a);pins=_z80_fetch(cpu,pins); goto finish_61; // DEC A (0)
finish_61:
    board_finish_slice(b,pins,elapsed,61); return elapsed;
fast_62:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_721; // LD A,n (0)
fast_63:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    { const uint8_t xy=((b->q^cpu->f)|cpu->a)&(Z80_YF|Z80_XF); _z80_ccf(cpu); cpu->f=(cpu->f&~(Z80_YF|Z80_XF))|xy; }pins=_z80_fetch(cpu,pins); goto finish_63; // CCF (0)
finish_63:
    board_finish_slice(b,pins,elapsed,63); return elapsed;
fast_64:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->b=cpu->b;pins=_z80_fetch(cpu,pins); goto finish_64; // LD B,B (0)
finish_64:
    board_finish_slice(b,pins,elapsed,64); return elapsed;
fast_65:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->b=cpu->c;pins=_z80_fetch(cpu,pins); goto finish_65; // LD B,C (0)
finish_65:
    board_finish_slice(b,pins,elapsed,65); return elapsed;
fast_66:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->b=cpu->d;pins=_z80_fetch(cpu,pins); goto finish_66; // LD B,D (0)
finish_66:
    board_finish_slice(b,pins,elapsed,66); return elapsed;
fast_67:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->b=cpu->e;pins=_z80_fetch(cpu,pins); goto finish_67; // LD B,E (0)
finish_67:
    board_finish_slice(b,pins,elapsed,67); return elapsed;
fast_68:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->b=cpu->hlx[cpu->hlx_idx].h;pins=_z80_fetch(cpu,pins); goto finish_68; // LD B,H (0)
finish_68:
    board_finish_slice(b,pins,elapsed,68); return elapsed;
fast_69:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->b=cpu->hlx[cpu->hlx_idx].l;pins=_z80_fetch(cpu,pins); goto finish_69; // LD B,L (0)
finish_69:
    board_finish_slice(b,pins,elapsed,69); return elapsed;
fast_70:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_724; // LD B,(HL) (0)
fast_71:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->b=cpu->a;pins=_z80_fetch(cpu,pins); goto finish_71; // LD B,A (0)
finish_71:
    board_finish_slice(b,pins,elapsed,71); return elapsed;
fast_72:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->c=cpu->b;pins=_z80_fetch(cpu,pins); goto finish_72; // LD C,B (0)
finish_72:
    board_finish_slice(b,pins,elapsed,72); return elapsed;
fast_73:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->c=cpu->c;pins=_z80_fetch(cpu,pins); goto finish_73; // LD C,C (0)
finish_73:
    board_finish_slice(b,pins,elapsed,73); return elapsed;
fast_74:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->c=cpu->d;pins=_z80_fetch(cpu,pins); goto finish_74; // LD C,D (0)
finish_74:
    board_finish_slice(b,pins,elapsed,74); return elapsed;
fast_75:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->c=cpu->e;pins=_z80_fetch(cpu,pins); goto finish_75; // LD C,E (0)
finish_75:
    board_finish_slice(b,pins,elapsed,75); return elapsed;
fast_76:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->c=cpu->hlx[cpu->hlx_idx].h;pins=_z80_fetch(cpu,pins); goto finish_76; // LD C,H (0)
finish_76:
    board_finish_slice(b,pins,elapsed,76); return elapsed;
fast_77:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->c=cpu->hlx[cpu->hlx_idx].l;pins=_z80_fetch(cpu,pins); goto finish_77; // LD C,L (0)
finish_77:
    board_finish_slice(b,pins,elapsed,77); return elapsed;
fast_78:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_727; // LD C,(HL) (0)
fast_79:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->c=cpu->a;pins=_z80_fetch(cpu,pins); goto finish_79; // LD C,A (0)
finish_79:
    board_finish_slice(b,pins,elapsed,79); return elapsed;
fast_80:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->d=cpu->b;pins=_z80_fetch(cpu,pins); goto finish_80; // LD D,B (0)
finish_80:
    board_finish_slice(b,pins,elapsed,80); return elapsed;
fast_81:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->d=cpu->c;pins=_z80_fetch(cpu,pins); goto finish_81; // LD D,C (0)
finish_81:
    board_finish_slice(b,pins,elapsed,81); return elapsed;
fast_82:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->d=cpu->d;pins=_z80_fetch(cpu,pins); goto finish_82; // LD D,D (0)
finish_82:
    board_finish_slice(b,pins,elapsed,82); return elapsed;
fast_83:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->d=cpu->e;pins=_z80_fetch(cpu,pins); goto finish_83; // LD D,E (0)
finish_83:
    board_finish_slice(b,pins,elapsed,83); return elapsed;
fast_84:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->d=cpu->hlx[cpu->hlx_idx].h;pins=_z80_fetch(cpu,pins); goto finish_84; // LD D,H (0)
finish_84:
    board_finish_slice(b,pins,elapsed,84); return elapsed;
fast_85:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->d=cpu->hlx[cpu->hlx_idx].l;pins=_z80_fetch(cpu,pins); goto finish_85; // LD D,L (0)
finish_85:
    board_finish_slice(b,pins,elapsed,85); return elapsed;
fast_86:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_730; // LD D,(HL) (0)
fast_87:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->d=cpu->a;pins=_z80_fetch(cpu,pins); goto finish_87; // LD D,A (0)
finish_87:
    board_finish_slice(b,pins,elapsed,87); return elapsed;
fast_88:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->e=cpu->b;pins=_z80_fetch(cpu,pins); goto finish_88; // LD E,B (0)
finish_88:
    board_finish_slice(b,pins,elapsed,88); return elapsed;
fast_89:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->e=cpu->c;pins=_z80_fetch(cpu,pins); goto finish_89; // LD E,C (0)
finish_89:
    board_finish_slice(b,pins,elapsed,89); return elapsed;
fast_90:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->e=cpu->d;pins=_z80_fetch(cpu,pins); goto finish_90; // LD E,D (0)
finish_90:
    board_finish_slice(b,pins,elapsed,90); return elapsed;
fast_91:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->e=cpu->e;pins=_z80_fetch(cpu,pins); goto finish_91; // LD E,E (0)
finish_91:
    board_finish_slice(b,pins,elapsed,91); return elapsed;
fast_92:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->e=cpu->hlx[cpu->hlx_idx].h;pins=_z80_fetch(cpu,pins); goto finish_92; // LD E,H (0)
finish_92:
    board_finish_slice(b,pins,elapsed,92); return elapsed;
fast_93:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->e=cpu->hlx[cpu->hlx_idx].l;pins=_z80_fetch(cpu,pins); goto finish_93; // LD E,L (0)
finish_93:
    board_finish_slice(b,pins,elapsed,93); return elapsed;
fast_94:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_733; // LD E,(HL) (0)
fast_95:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->e=cpu->a;pins=_z80_fetch(cpu,pins); goto finish_95; // LD E,A (0)
finish_95:
    board_finish_slice(b,pins,elapsed,95); return elapsed;
fast_96:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->hlx[cpu->hlx_idx].h=cpu->b;pins=_z80_fetch(cpu,pins); goto finish_96; // LD H,B (0)
finish_96:
    board_finish_slice(b,pins,elapsed,96); return elapsed;
fast_97:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->hlx[cpu->hlx_idx].h=cpu->c;pins=_z80_fetch(cpu,pins); goto finish_97; // LD H,C (0)
finish_97:
    board_finish_slice(b,pins,elapsed,97); return elapsed;
fast_98:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->hlx[cpu->hlx_idx].h=cpu->d;pins=_z80_fetch(cpu,pins); goto finish_98; // LD H,D (0)
finish_98:
    board_finish_slice(b,pins,elapsed,98); return elapsed;
fast_99:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->hlx[cpu->hlx_idx].h=cpu->e;pins=_z80_fetch(cpu,pins); goto finish_99; // LD H,E (0)
finish_99:
    board_finish_slice(b,pins,elapsed,99); return elapsed;
fast_100:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->hlx[cpu->hlx_idx].h=cpu->hlx[cpu->hlx_idx].h;pins=_z80_fetch(cpu,pins); goto finish_100; // LD H,H (0)
finish_100:
    board_finish_slice(b,pins,elapsed,100); return elapsed;
fast_101:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->hlx[cpu->hlx_idx].h=cpu->hlx[cpu->hlx_idx].l;pins=_z80_fetch(cpu,pins); goto finish_101; // LD H,L (0)
finish_101:
    board_finish_slice(b,pins,elapsed,101); return elapsed;
fast_102:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_736; // LD H,(HL) (0)
fast_103:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->hlx[cpu->hlx_idx].h=cpu->a;pins=_z80_fetch(cpu,pins); goto finish_103; // LD H,A (0)
finish_103:
    board_finish_slice(b,pins,elapsed,103); return elapsed;
fast_104:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->hlx[cpu->hlx_idx].l=cpu->b;pins=_z80_fetch(cpu,pins); goto finish_104; // LD L,B (0)
finish_104:
    board_finish_slice(b,pins,elapsed,104); return elapsed;
fast_105:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->hlx[cpu->hlx_idx].l=cpu->c;pins=_z80_fetch(cpu,pins); goto finish_105; // LD L,C (0)
finish_105:
    board_finish_slice(b,pins,elapsed,105); return elapsed;
fast_106:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->hlx[cpu->hlx_idx].l=cpu->d;pins=_z80_fetch(cpu,pins); goto finish_106; // LD L,D (0)
finish_106:
    board_finish_slice(b,pins,elapsed,106); return elapsed;
fast_107:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->hlx[cpu->hlx_idx].l=cpu->e;pins=_z80_fetch(cpu,pins); goto finish_107; // LD L,E (0)
finish_107:
    board_finish_slice(b,pins,elapsed,107); return elapsed;
fast_108:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->hlx[cpu->hlx_idx].l=cpu->hlx[cpu->hlx_idx].h;pins=_z80_fetch(cpu,pins); goto finish_108; // LD L,H (0)
finish_108:
    board_finish_slice(b,pins,elapsed,108); return elapsed;
fast_109:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->hlx[cpu->hlx_idx].l=cpu->hlx[cpu->hlx_idx].l;pins=_z80_fetch(cpu,pins); goto finish_109; // LD L,L (0)
finish_109:
    board_finish_slice(b,pins,elapsed,109); return elapsed;
fast_110:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_739; // LD L,(HL) (0)
fast_111:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->hlx[cpu->hlx_idx].l=cpu->a;pins=_z80_fetch(cpu,pins); goto finish_111; // LD L,A (0)
finish_111:
    board_finish_slice(b,pins,elapsed,111); return elapsed;
fast_112:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_742; // LD (HL),B (0)
fast_113:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_745; // LD (HL),C (0)
fast_114:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_748; // LD (HL),D (0)
fast_115:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_751; // LD (HL),E (0)
fast_116:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_754; // LD (HL),H (0)
fast_117:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_757; // LD (HL),L (0)
fast_118:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_halt(cpu,pins);pins=_z80_fetch(cpu,pins); goto finish_118; // HALT (0)
finish_118:
    board_finish_slice(b,pins,elapsed,118); return elapsed;
fast_119:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_760; // LD (HL),A (0)
fast_120:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->a=cpu->b;pins=_z80_fetch(cpu,pins); goto finish_120; // LD A,B (0)
finish_120:
    board_finish_slice(b,pins,elapsed,120); return elapsed;
fast_121:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->a=cpu->c;pins=_z80_fetch(cpu,pins); goto finish_121; // LD A,C (0)
finish_121:
    board_finish_slice(b,pins,elapsed,121); return elapsed;
fast_122:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->a=cpu->d;pins=_z80_fetch(cpu,pins); goto finish_122; // LD A,D (0)
finish_122:
    board_finish_slice(b,pins,elapsed,122); return elapsed;
fast_123:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->a=cpu->e;pins=_z80_fetch(cpu,pins); goto finish_123; // LD A,E (0)
finish_123:
    board_finish_slice(b,pins,elapsed,123); return elapsed;
fast_124:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->a=cpu->hlx[cpu->hlx_idx].h;pins=_z80_fetch(cpu,pins); goto finish_124; // LD A,H (0)
finish_124:
    board_finish_slice(b,pins,elapsed,124); return elapsed;
fast_125:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->a=cpu->hlx[cpu->hlx_idx].l;pins=_z80_fetch(cpu,pins); goto finish_125; // LD A,L (0)
finish_125:
    board_finish_slice(b,pins,elapsed,125); return elapsed;
fast_126:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_763; // LD A,(HL) (0)
fast_127:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->a=cpu->a;pins=_z80_fetch(cpu,pins); goto finish_127; // LD A,A (0)
finish_127:
    board_finish_slice(b,pins,elapsed,127); return elapsed;
fast_128:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_add8(cpu,cpu->b);pins=_z80_fetch(cpu,pins); goto finish_128; // ADD B (0)
finish_128:
    board_finish_slice(b,pins,elapsed,128); return elapsed;
fast_129:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_add8(cpu,cpu->c);pins=_z80_fetch(cpu,pins); goto finish_129; // ADD C (0)
finish_129:
    board_finish_slice(b,pins,elapsed,129); return elapsed;
fast_130:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_add8(cpu,cpu->d);pins=_z80_fetch(cpu,pins); goto finish_130; // ADD D (0)
finish_130:
    board_finish_slice(b,pins,elapsed,130); return elapsed;
fast_131:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_add8(cpu,cpu->e);pins=_z80_fetch(cpu,pins); goto finish_131; // ADD E (0)
finish_131:
    board_finish_slice(b,pins,elapsed,131); return elapsed;
fast_132:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_add8(cpu,cpu->hlx[cpu->hlx_idx].h);pins=_z80_fetch(cpu,pins); goto finish_132; // ADD H (0)
finish_132:
    board_finish_slice(b,pins,elapsed,132); return elapsed;
fast_133:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_add8(cpu,cpu->hlx[cpu->hlx_idx].l);pins=_z80_fetch(cpu,pins); goto finish_133; // ADD L (0)
finish_133:
    board_finish_slice(b,pins,elapsed,133); return elapsed;
fast_134:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_766; // ADD (HL) (0)
fast_135:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_add8(cpu,cpu->a);pins=_z80_fetch(cpu,pins); goto finish_135; // ADD A (0)
finish_135:
    board_finish_slice(b,pins,elapsed,135); return elapsed;
fast_136:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_adc8(cpu,cpu->b);pins=_z80_fetch(cpu,pins); goto finish_136; // ADC B (0)
finish_136:
    board_finish_slice(b,pins,elapsed,136); return elapsed;
fast_137:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_adc8(cpu,cpu->c);pins=_z80_fetch(cpu,pins); goto finish_137; // ADC C (0)
finish_137:
    board_finish_slice(b,pins,elapsed,137); return elapsed;
fast_138:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_adc8(cpu,cpu->d);pins=_z80_fetch(cpu,pins); goto finish_138; // ADC D (0)
finish_138:
    board_finish_slice(b,pins,elapsed,138); return elapsed;
fast_139:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_adc8(cpu,cpu->e);pins=_z80_fetch(cpu,pins); goto finish_139; // ADC E (0)
finish_139:
    board_finish_slice(b,pins,elapsed,139); return elapsed;
fast_140:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_adc8(cpu,cpu->hlx[cpu->hlx_idx].h);pins=_z80_fetch(cpu,pins); goto finish_140; // ADC H (0)
finish_140:
    board_finish_slice(b,pins,elapsed,140); return elapsed;
fast_141:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_adc8(cpu,cpu->hlx[cpu->hlx_idx].l);pins=_z80_fetch(cpu,pins); goto finish_141; // ADC L (0)
finish_141:
    board_finish_slice(b,pins,elapsed,141); return elapsed;
fast_142:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_769; // ADC (HL) (0)
fast_143:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_adc8(cpu,cpu->a);pins=_z80_fetch(cpu,pins); goto finish_143; // ADC A (0)
finish_143:
    board_finish_slice(b,pins,elapsed,143); return elapsed;
fast_144:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_sub8(cpu,cpu->b);pins=_z80_fetch(cpu,pins); goto finish_144; // SUB B (0)
finish_144:
    board_finish_slice(b,pins,elapsed,144); return elapsed;
fast_145:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_sub8(cpu,cpu->c);pins=_z80_fetch(cpu,pins); goto finish_145; // SUB C (0)
finish_145:
    board_finish_slice(b,pins,elapsed,145); return elapsed;
fast_146:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_sub8(cpu,cpu->d);pins=_z80_fetch(cpu,pins); goto finish_146; // SUB D (0)
finish_146:
    board_finish_slice(b,pins,elapsed,146); return elapsed;
fast_147:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_sub8(cpu,cpu->e);pins=_z80_fetch(cpu,pins); goto finish_147; // SUB E (0)
finish_147:
    board_finish_slice(b,pins,elapsed,147); return elapsed;
fast_148:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_sub8(cpu,cpu->hlx[cpu->hlx_idx].h);pins=_z80_fetch(cpu,pins); goto finish_148; // SUB H (0)
finish_148:
    board_finish_slice(b,pins,elapsed,148); return elapsed;
fast_149:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_sub8(cpu,cpu->hlx[cpu->hlx_idx].l);pins=_z80_fetch(cpu,pins); goto finish_149; // SUB L (0)
finish_149:
    board_finish_slice(b,pins,elapsed,149); return elapsed;
fast_150:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_772; // SUB (HL) (0)
fast_151:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_sub8(cpu,cpu->a);pins=_z80_fetch(cpu,pins); goto finish_151; // SUB A (0)
finish_151:
    board_finish_slice(b,pins,elapsed,151); return elapsed;
fast_152:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_sbc8(cpu,cpu->b);pins=_z80_fetch(cpu,pins); goto finish_152; // SBC B (0)
finish_152:
    board_finish_slice(b,pins,elapsed,152); return elapsed;
fast_153:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_sbc8(cpu,cpu->c);pins=_z80_fetch(cpu,pins); goto finish_153; // SBC C (0)
finish_153:
    board_finish_slice(b,pins,elapsed,153); return elapsed;
fast_154:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_sbc8(cpu,cpu->d);pins=_z80_fetch(cpu,pins); goto finish_154; // SBC D (0)
finish_154:
    board_finish_slice(b,pins,elapsed,154); return elapsed;
fast_155:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_sbc8(cpu,cpu->e);pins=_z80_fetch(cpu,pins); goto finish_155; // SBC E (0)
finish_155:
    board_finish_slice(b,pins,elapsed,155); return elapsed;
fast_156:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_sbc8(cpu,cpu->hlx[cpu->hlx_idx].h);pins=_z80_fetch(cpu,pins); goto finish_156; // SBC H (0)
finish_156:
    board_finish_slice(b,pins,elapsed,156); return elapsed;
fast_157:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_sbc8(cpu,cpu->hlx[cpu->hlx_idx].l);pins=_z80_fetch(cpu,pins); goto finish_157; // SBC L (0)
finish_157:
    board_finish_slice(b,pins,elapsed,157); return elapsed;
fast_158:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_775; // SBC (HL) (0)
fast_159:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_sbc8(cpu,cpu->a);pins=_z80_fetch(cpu,pins); goto finish_159; // SBC A (0)
finish_159:
    board_finish_slice(b,pins,elapsed,159); return elapsed;
fast_160:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_and8(cpu,cpu->b);pins=_z80_fetch(cpu,pins); goto finish_160; // AND B (0)
finish_160:
    board_finish_slice(b,pins,elapsed,160); return elapsed;
fast_161:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_and8(cpu,cpu->c);pins=_z80_fetch(cpu,pins); goto finish_161; // AND C (0)
finish_161:
    board_finish_slice(b,pins,elapsed,161); return elapsed;
fast_162:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_and8(cpu,cpu->d);pins=_z80_fetch(cpu,pins); goto finish_162; // AND D (0)
finish_162:
    board_finish_slice(b,pins,elapsed,162); return elapsed;
fast_163:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_and8(cpu,cpu->e);pins=_z80_fetch(cpu,pins); goto finish_163; // AND E (0)
finish_163:
    board_finish_slice(b,pins,elapsed,163); return elapsed;
fast_164:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_and8(cpu,cpu->hlx[cpu->hlx_idx].h);pins=_z80_fetch(cpu,pins); goto finish_164; // AND H (0)
finish_164:
    board_finish_slice(b,pins,elapsed,164); return elapsed;
fast_165:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_and8(cpu,cpu->hlx[cpu->hlx_idx].l);pins=_z80_fetch(cpu,pins); goto finish_165; // AND L (0)
finish_165:
    board_finish_slice(b,pins,elapsed,165); return elapsed;
fast_166:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_778; // AND (HL) (0)
fast_167:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_and8(cpu,cpu->a);pins=_z80_fetch(cpu,pins); goto finish_167; // AND A (0)
finish_167:
    board_finish_slice(b,pins,elapsed,167); return elapsed;
fast_168:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_xor8(cpu,cpu->b);pins=_z80_fetch(cpu,pins); goto finish_168; // XOR B (0)
finish_168:
    board_finish_slice(b,pins,elapsed,168); return elapsed;
fast_169:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_xor8(cpu,cpu->c);pins=_z80_fetch(cpu,pins); goto finish_169; // XOR C (0)
finish_169:
    board_finish_slice(b,pins,elapsed,169); return elapsed;
fast_170:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_xor8(cpu,cpu->d);pins=_z80_fetch(cpu,pins); goto finish_170; // XOR D (0)
finish_170:
    board_finish_slice(b,pins,elapsed,170); return elapsed;
fast_171:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_xor8(cpu,cpu->e);pins=_z80_fetch(cpu,pins); goto finish_171; // XOR E (0)
finish_171:
    board_finish_slice(b,pins,elapsed,171); return elapsed;
fast_172:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_xor8(cpu,cpu->hlx[cpu->hlx_idx].h);pins=_z80_fetch(cpu,pins); goto finish_172; // XOR H (0)
finish_172:
    board_finish_slice(b,pins,elapsed,172); return elapsed;
fast_173:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_xor8(cpu,cpu->hlx[cpu->hlx_idx].l);pins=_z80_fetch(cpu,pins); goto finish_173; // XOR L (0)
finish_173:
    board_finish_slice(b,pins,elapsed,173); return elapsed;
fast_174:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_781; // XOR (HL) (0)
fast_175:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_xor8(cpu,cpu->a);pins=_z80_fetch(cpu,pins); goto finish_175; // XOR A (0)
finish_175:
    board_finish_slice(b,pins,elapsed,175); return elapsed;
fast_176:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_or8(cpu,cpu->b);pins=_z80_fetch(cpu,pins); goto finish_176; // OR B (0)
finish_176:
    board_finish_slice(b,pins,elapsed,176); return elapsed;
fast_177:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_or8(cpu,cpu->c);pins=_z80_fetch(cpu,pins); goto finish_177; // OR C (0)
finish_177:
    board_finish_slice(b,pins,elapsed,177); return elapsed;
fast_178:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_or8(cpu,cpu->d);pins=_z80_fetch(cpu,pins); goto finish_178; // OR D (0)
finish_178:
    board_finish_slice(b,pins,elapsed,178); return elapsed;
fast_179:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_or8(cpu,cpu->e);pins=_z80_fetch(cpu,pins); goto finish_179; // OR E (0)
finish_179:
    board_finish_slice(b,pins,elapsed,179); return elapsed;
fast_180:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_or8(cpu,cpu->hlx[cpu->hlx_idx].h);pins=_z80_fetch(cpu,pins); goto finish_180; // OR H (0)
finish_180:
    board_finish_slice(b,pins,elapsed,180); return elapsed;
fast_181:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_or8(cpu,cpu->hlx[cpu->hlx_idx].l);pins=_z80_fetch(cpu,pins); goto finish_181; // OR L (0)
finish_181:
    board_finish_slice(b,pins,elapsed,181); return elapsed;
fast_182:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_784; // OR (HL) (0)
fast_183:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_or8(cpu,cpu->a);pins=_z80_fetch(cpu,pins); goto finish_183; // OR A (0)
finish_183:
    board_finish_slice(b,pins,elapsed,183); return elapsed;
fast_184:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_cp8(cpu,cpu->b);pins=_z80_fetch(cpu,pins); goto finish_184; // CP B (0)
finish_184:
    board_finish_slice(b,pins,elapsed,184); return elapsed;
fast_185:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_cp8(cpu,cpu->c);pins=_z80_fetch(cpu,pins); goto finish_185; // CP C (0)
finish_185:
    board_finish_slice(b,pins,elapsed,185); return elapsed;
fast_186:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_cp8(cpu,cpu->d);pins=_z80_fetch(cpu,pins); goto finish_186; // CP D (0)
finish_186:
    board_finish_slice(b,pins,elapsed,186); return elapsed;
fast_187:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_cp8(cpu,cpu->e);pins=_z80_fetch(cpu,pins); goto finish_187; // CP E (0)
finish_187:
    board_finish_slice(b,pins,elapsed,187); return elapsed;
fast_188:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_cp8(cpu,cpu->hlx[cpu->hlx_idx].h);pins=_z80_fetch(cpu,pins); goto finish_188; // CP H (0)
finish_188:
    board_finish_slice(b,pins,elapsed,188); return elapsed;
fast_189:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_cp8(cpu,cpu->hlx[cpu->hlx_idx].l);pins=_z80_fetch(cpu,pins); goto finish_189; // CP L (0)
finish_189:
    board_finish_slice(b,pins,elapsed,189); return elapsed;
fast_190:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_787; // CP (HL) (0)
fast_191:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_cp8(cpu,cpu->a);pins=_z80_fetch(cpu,pins); goto finish_191; // CP A (0)
finish_191:
    board_finish_slice(b,pins,elapsed,191); return elapsed;
fast_192:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    if(!_cc_nz){goto fast_796;};goto fast_790; // RET NZ (0)
fast_193:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_797; // POP BC (0)
fast_194:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_803; // JP NZ,nn (0)
fast_195:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_809; // JP nn (0)
fast_196:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_815; // CALL NZ,nn (0)
fast_197:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_828; // PUSH BC (0)
fast_198:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_835; // ADD n (0)
fast_199:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_838; // RST 0h (0)
fast_200:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    if(!_cc_z){goto fast_851;};goto fast_845; // RET Z (0)
fast_201:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_852; // RET (0)
fast_202:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_858; // JP Z,nn (0)
fast_203:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _fetch_cb();goto finish_203; // CB prefix (0)
finish_203:
    board_finish_slice(b,pins,elapsed,203); return elapsed;
fast_204:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_864; // CALL Z,nn (0)
fast_205:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_877; // CALL nn (0)
fast_206:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_890; // ADC n (0)
fast_207:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_893; // RST 8h (0)
fast_208:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    if(!_cc_nc){goto fast_906;};goto fast_900; // RET NC (0)
fast_209:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_907; // POP DE (0)
fast_210:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_913; // JP NC,nn (0)
fast_211:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_919; // OUT (n),A (0)
fast_212:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_926; // CALL NC,nn (0)
fast_213:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_939; // PUSH DE (0)
fast_214:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_946; // SUB n (0)
fast_215:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_949; // RST 10h (0)
fast_216:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    if(!_cc_c){goto fast_962;};goto fast_956; // RET C (0)
fast_217:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_exx(cpu);pins=_z80_fetch(cpu,pins); goto finish_217; // EXX (0)
finish_217:
    board_finish_slice(b,pins,elapsed,217); return elapsed;
fast_218:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_963; // JP C,nn (0)
fast_219:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_969; // IN A,(n) (0)
fast_220:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_976; // CALL C,nn (0)
fast_221:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _fetch_dd();goto finish_221; // DD prefix (0)
finish_221:
    board_finish_slice(b,pins,elapsed,221); return elapsed;
fast_222:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_989; // SBC n (0)
fast_223:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_992; // RST 18h (0)
fast_224:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    if(!_cc_po){goto fast_1005;};goto fast_999; // RET PO (0)
fast_225:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1006; // POP HL (0)
fast_226:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1012; // JP PO,nn (0)
fast_227:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1018; // EX (SP),HL (0)
fast_228:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1033; // CALL PO,nn (0)
fast_229:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1046; // PUSH HL (0)
fast_230:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1053; // AND n (0)
fast_231:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1056; // RST 20h (0)
fast_232:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    if(!_cc_pe){goto fast_1069;};goto fast_1063; // RET PE (0)
fast_233:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->pc=cpu->hlx[cpu->hlx_idx].hl;pins=_z80_fetch(cpu,pins); goto finish_233; // JP HL (0)
finish_233:
    board_finish_slice(b,pins,elapsed,233); return elapsed;
fast_234:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1070; // JP PE,nn (0)
fast_235:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_ex_de_hl(cpu);pins=_z80_fetch(cpu,pins); goto finish_235; // EX DE,HL (0)
finish_235:
    board_finish_slice(b,pins,elapsed,235); return elapsed;
fast_236:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1076; // CALL PE,nn (0)
fast_237:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _fetch_ed();goto finish_237; // ED prefix (0)
finish_237:
    board_finish_slice(b,pins,elapsed,237); return elapsed;
fast_238:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1089; // XOR n (0)
fast_239:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1092; // RST 28h (0)
fast_240:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    if(!_cc_p){goto fast_1105;};goto fast_1099; // RET P (0)
fast_241:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1106; // POP AF (0)
fast_242:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1112; // JP P,nn (0)
fast_243:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->iff1=cpu->iff2=false;pins=_z80_fetch(cpu,pins); goto finish_243; // DI (0)
finish_243:
    board_finish_slice(b,pins,elapsed,243); return elapsed;
fast_244:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1118; // CALL P,nn (0)
fast_245:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1131; // PUSH AF (0)
fast_246:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1138; // OR n (0)
fast_247:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1141; // RST 30h (0)
fast_248:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    if(!_cc_m){goto fast_1154;};goto fast_1148; // RET M (0)
fast_249:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->sp=cpu->hlx[cpu->hlx_idx].hl;goto fast_1155; // LD SP,HL (0)
fast_250:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1157; // JP M,nn (0)
fast_251:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->iff1=cpu->iff2=false;pins=_z80_fetch(cpu,pins);cpu->iff1=cpu->iff2=true;goto finish_251; // EI (0)
finish_251:
    board_finish_slice(b,pins,elapsed,251); return elapsed;
fast_252:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1163; // CALL M,nn (0)
fast_253:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _fetch_fd();goto finish_253; // FD prefix (0)
finish_253:
    board_finish_slice(b,pins,elapsed,253); return elapsed;
fast_254:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1176; // CP n (0)
fast_255:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1179; // RST 38h (0)
fast_256:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_256; // ED NOP (0)
finish_256:
    board_finish_slice(b,pins,elapsed,256); return elapsed;
fast_257:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_257; // ED NOP (0)
finish_257:
    board_finish_slice(b,pins,elapsed,257); return elapsed;
fast_258:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_258; // ED NOP (0)
finish_258:
    board_finish_slice(b,pins,elapsed,258); return elapsed;
fast_259:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_259; // ED NOP (0)
finish_259:
    board_finish_slice(b,pins,elapsed,259); return elapsed;
fast_260:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_260; // ED NOP (0)
finish_260:
    board_finish_slice(b,pins,elapsed,260); return elapsed;
fast_261:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_261; // ED NOP (0)
finish_261:
    board_finish_slice(b,pins,elapsed,261); return elapsed;
fast_262:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_262; // ED NOP (0)
finish_262:
    board_finish_slice(b,pins,elapsed,262); return elapsed;
fast_263:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_263; // ED NOP (0)
finish_263:
    board_finish_slice(b,pins,elapsed,263); return elapsed;
fast_264:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_264; // ED NOP (0)
finish_264:
    board_finish_slice(b,pins,elapsed,264); return elapsed;
fast_265:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_265; // ED NOP (0)
finish_265:
    board_finish_slice(b,pins,elapsed,265); return elapsed;
fast_266:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_266; // ED NOP (0)
finish_266:
    board_finish_slice(b,pins,elapsed,266); return elapsed;
fast_267:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_267; // ED NOP (0)
finish_267:
    board_finish_slice(b,pins,elapsed,267); return elapsed;
fast_268:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_268; // ED NOP (0)
finish_268:
    board_finish_slice(b,pins,elapsed,268); return elapsed;
fast_269:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_269; // ED NOP (0)
finish_269:
    board_finish_slice(b,pins,elapsed,269); return elapsed;
fast_270:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_270; // ED NOP (0)
finish_270:
    board_finish_slice(b,pins,elapsed,270); return elapsed;
fast_271:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_271; // ED NOP (0)
finish_271:
    board_finish_slice(b,pins,elapsed,271); return elapsed;
fast_272:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_272; // ED NOP (0)
finish_272:
    board_finish_slice(b,pins,elapsed,272); return elapsed;
fast_273:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_273; // ED NOP (0)
finish_273:
    board_finish_slice(b,pins,elapsed,273); return elapsed;
fast_274:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_274; // ED NOP (0)
finish_274:
    board_finish_slice(b,pins,elapsed,274); return elapsed;
fast_275:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_275; // ED NOP (0)
finish_275:
    board_finish_slice(b,pins,elapsed,275); return elapsed;
fast_276:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_276; // ED NOP (0)
finish_276:
    board_finish_slice(b,pins,elapsed,276); return elapsed;
fast_277:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_277; // ED NOP (0)
finish_277:
    board_finish_slice(b,pins,elapsed,277); return elapsed;
fast_278:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_278; // ED NOP (0)
finish_278:
    board_finish_slice(b,pins,elapsed,278); return elapsed;
fast_279:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_279; // ED NOP (0)
finish_279:
    board_finish_slice(b,pins,elapsed,279); return elapsed;
fast_280:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_280; // ED NOP (0)
finish_280:
    board_finish_slice(b,pins,elapsed,280); return elapsed;
fast_281:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_281; // ED NOP (0)
finish_281:
    board_finish_slice(b,pins,elapsed,281); return elapsed;
fast_282:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_282; // ED NOP (0)
finish_282:
    board_finish_slice(b,pins,elapsed,282); return elapsed;
fast_283:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_283; // ED NOP (0)
finish_283:
    board_finish_slice(b,pins,elapsed,283); return elapsed;
fast_284:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_284; // ED NOP (0)
finish_284:
    board_finish_slice(b,pins,elapsed,284); return elapsed;
fast_285:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_285; // ED NOP (0)
finish_285:
    board_finish_slice(b,pins,elapsed,285); return elapsed;
fast_286:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_286; // ED NOP (0)
finish_286:
    board_finish_slice(b,pins,elapsed,286); return elapsed;
fast_287:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_287; // ED NOP (0)
finish_287:
    board_finish_slice(b,pins,elapsed,287); return elapsed;
fast_288:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_288; // ED NOP (0)
finish_288:
    board_finish_slice(b,pins,elapsed,288); return elapsed;
fast_289:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_289; // ED NOP (0)
finish_289:
    board_finish_slice(b,pins,elapsed,289); return elapsed;
fast_290:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_290; // ED NOP (0)
finish_290:
    board_finish_slice(b,pins,elapsed,290); return elapsed;
fast_291:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_291; // ED NOP (0)
finish_291:
    board_finish_slice(b,pins,elapsed,291); return elapsed;
fast_292:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_292; // ED NOP (0)
finish_292:
    board_finish_slice(b,pins,elapsed,292); return elapsed;
fast_293:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_293; // ED NOP (0)
finish_293:
    board_finish_slice(b,pins,elapsed,293); return elapsed;
fast_294:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_294; // ED NOP (0)
finish_294:
    board_finish_slice(b,pins,elapsed,294); return elapsed;
fast_295:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_295; // ED NOP (0)
finish_295:
    board_finish_slice(b,pins,elapsed,295); return elapsed;
fast_296:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_296; // ED NOP (0)
finish_296:
    board_finish_slice(b,pins,elapsed,296); return elapsed;
fast_297:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_297; // ED NOP (0)
finish_297:
    board_finish_slice(b,pins,elapsed,297); return elapsed;
fast_298:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_298; // ED NOP (0)
finish_298:
    board_finish_slice(b,pins,elapsed,298); return elapsed;
fast_299:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_299; // ED NOP (0)
finish_299:
    board_finish_slice(b,pins,elapsed,299); return elapsed;
fast_300:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_300; // ED NOP (0)
finish_300:
    board_finish_slice(b,pins,elapsed,300); return elapsed;
fast_301:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_301; // ED NOP (0)
finish_301:
    board_finish_slice(b,pins,elapsed,301); return elapsed;
fast_302:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_302; // ED NOP (0)
finish_302:
    board_finish_slice(b,pins,elapsed,302); return elapsed;
fast_303:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_303; // ED NOP (0)
finish_303:
    board_finish_slice(b,pins,elapsed,303); return elapsed;
fast_304:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_304; // ED NOP (0)
finish_304:
    board_finish_slice(b,pins,elapsed,304); return elapsed;
fast_305:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_305; // ED NOP (0)
finish_305:
    board_finish_slice(b,pins,elapsed,305); return elapsed;
fast_306:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_306; // ED NOP (0)
finish_306:
    board_finish_slice(b,pins,elapsed,306); return elapsed;
fast_307:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_307; // ED NOP (0)
finish_307:
    board_finish_slice(b,pins,elapsed,307); return elapsed;
fast_308:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_308; // ED NOP (0)
finish_308:
    board_finish_slice(b,pins,elapsed,308); return elapsed;
fast_309:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_309; // ED NOP (0)
finish_309:
    board_finish_slice(b,pins,elapsed,309); return elapsed;
fast_310:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_310; // ED NOP (0)
finish_310:
    board_finish_slice(b,pins,elapsed,310); return elapsed;
fast_311:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_311; // ED NOP (0)
finish_311:
    board_finish_slice(b,pins,elapsed,311); return elapsed;
fast_312:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_312; // ED NOP (0)
finish_312:
    board_finish_slice(b,pins,elapsed,312); return elapsed;
fast_313:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_313; // ED NOP (0)
finish_313:
    board_finish_slice(b,pins,elapsed,313); return elapsed;
fast_314:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_314; // ED NOP (0)
finish_314:
    board_finish_slice(b,pins,elapsed,314); return elapsed;
fast_315:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_315; // ED NOP (0)
finish_315:
    board_finish_slice(b,pins,elapsed,315); return elapsed;
fast_316:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_316; // ED NOP (0)
finish_316:
    board_finish_slice(b,pins,elapsed,316); return elapsed;
fast_317:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_317; // ED NOP (0)
finish_317:
    board_finish_slice(b,pins,elapsed,317); return elapsed;
fast_318:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_318; // ED NOP (0)
finish_318:
    board_finish_slice(b,pins,elapsed,318); return elapsed;
fast_319:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_319; // ED NOP (0)
finish_319:
    board_finish_slice(b,pins,elapsed,319); return elapsed;
fast_320:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1186; // IN B,(C) (0)
fast_321:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1190; // OUT (C),B (0)
fast_322:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_sbc16(cpu,cpu->bc);goto fast_1194; // SBC HL,BC (0)
fast_323:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1201; // LD (nn),BC (0)
fast_324:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_neg8(cpu);pins=_z80_fetch(cpu,pins); goto finish_324; // NEG (0)
finish_324:
    board_finish_slice(b,pins,elapsed,324); return elapsed;
fast_325:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1213; // RETN (0)
fast_326:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->im=0;pins=_z80_fetch(cpu,pins); goto finish_326; // IM 0 (0)
finish_326:
    board_finish_slice(b,pins,elapsed,326); return elapsed;
fast_327:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1219; // LD I,A (0)
fast_328:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1220; // IN C,(C) (0)
fast_329:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1224; // OUT (C),C (0)
fast_330:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_adc16(cpu,cpu->bc);goto fast_1228; // ADC HL,BC (0)
fast_331:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1235; // LD BC,(nn) (0)
fast_332:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_neg8(cpu);pins=_z80_fetch(cpu,pins); goto finish_332; // NEG (0)
finish_332:
    board_finish_slice(b,pins,elapsed,332); return elapsed;
fast_333:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1247; // RETI (0)
fast_334:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->im=0;pins=_z80_fetch(cpu,pins); goto finish_334; // IM 0 (0)
finish_334:
    board_finish_slice(b,pins,elapsed,334); return elapsed;
fast_335:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1253; // LD R,A (0)
fast_336:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1254; // IN D,(C) (0)
fast_337:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1258; // OUT (C),D (0)
fast_338:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_sbc16(cpu,cpu->de);goto fast_1262; // SBC HL,DE (0)
fast_339:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1269; // LD (nn),DE (0)
fast_340:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_neg8(cpu);pins=_z80_fetch(cpu,pins); goto finish_340; // NEG (0)
finish_340:
    board_finish_slice(b,pins,elapsed,340); return elapsed;
fast_341:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1247; // RETI (0)
fast_342:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->im=1;pins=_z80_fetch(cpu,pins); goto finish_342; // IM 1 (0)
finish_342:
    board_finish_slice(b,pins,elapsed,342); return elapsed;
fast_343:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1282; // LD A,I (0)
fast_344:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1283; // IN E,(C) (0)
fast_345:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1287; // OUT (C),E (0)
fast_346:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_adc16(cpu,cpu->de);goto fast_1291; // ADC HL,DE (0)
fast_347:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1298; // LD DE,(nn) (0)
fast_348:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_neg8(cpu);pins=_z80_fetch(cpu,pins); goto finish_348; // NEG (0)
finish_348:
    board_finish_slice(b,pins,elapsed,348); return elapsed;
fast_349:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1247; // RETI (0)
fast_350:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->im=2;pins=_z80_fetch(cpu,pins); goto finish_350; // IM 2 (0)
finish_350:
    board_finish_slice(b,pins,elapsed,350); return elapsed;
fast_351:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1311; // LD A,R (0)
fast_352:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1312; // IN H,(C) (0)
fast_353:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1316; // OUT (C),H (0)
fast_354:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_sbc16(cpu,cpu->hl);goto fast_1320; // SBC HL,HL (0)
fast_355:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1327; // LD (nn),HL (0)
fast_356:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_neg8(cpu);pins=_z80_fetch(cpu,pins); goto finish_356; // NEG (0)
finish_356:
    board_finish_slice(b,pins,elapsed,356); return elapsed;
fast_357:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1247; // RETI (0)
fast_358:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->im=0;pins=_z80_fetch(cpu,pins); goto finish_358; // IM 0 (0)
finish_358:
    board_finish_slice(b,pins,elapsed,358); return elapsed;
fast_359:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1340; // RRD (0)
fast_360:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1350; // IN L,(C) (0)
fast_361:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1354; // OUT (C),L (0)
fast_362:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_adc16(cpu,cpu->hl);goto fast_1358; // ADC HL,HL (0)
fast_363:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1365; // LD HL,(nn) (0)
fast_364:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_neg8(cpu);pins=_z80_fetch(cpu,pins); goto finish_364; // NEG (0)
finish_364:
    board_finish_slice(b,pins,elapsed,364); return elapsed;
fast_365:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1247; // RETI (0)
fast_366:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->im=0;pins=_z80_fetch(cpu,pins); goto finish_366; // IM 0 (0)
finish_366:
    board_finish_slice(b,pins,elapsed,366); return elapsed;
fast_367:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1378; // RLD (0)
fast_368:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1388; // IN (C) (0)
fast_369:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1392; // OUT (C),0 (0)
fast_370:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_sbc16(cpu,cpu->sp);goto fast_1396; // SBC HL,SP (0)
fast_371:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1403; // LD (nn),SP (0)
fast_372:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_neg8(cpu);pins=_z80_fetch(cpu,pins); goto finish_372; // NEG (0)
finish_372:
    board_finish_slice(b,pins,elapsed,372); return elapsed;
fast_373:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1247; // RETI (0)
fast_374:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->im=1;pins=_z80_fetch(cpu,pins); goto finish_374; // IM 1 (0)
finish_374:
    board_finish_slice(b,pins,elapsed,374); return elapsed;
fast_375:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_375; // ED NOP (0)
finish_375:
    board_finish_slice(b,pins,elapsed,375); return elapsed;
fast_376:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1416; // IN A,(C) (0)
fast_377:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1420; // OUT (C),A (0)
fast_378:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_adc16(cpu,cpu->sp);goto fast_1424; // ADC HL,SP (0)
fast_379:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1431; // LD SP,(nn) (0)
fast_380:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_neg8(cpu);pins=_z80_fetch(cpu,pins); goto finish_380; // NEG (0)
finish_380:
    board_finish_slice(b,pins,elapsed,380); return elapsed;
fast_381:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1247; // RETI (0)
fast_382:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->im=2;pins=_z80_fetch(cpu,pins); goto finish_382; // IM 2 (0)
finish_382:
    board_finish_slice(b,pins,elapsed,382); return elapsed;
fast_383:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_383; // ED NOP (0)
finish_383:
    board_finish_slice(b,pins,elapsed,383); return elapsed;
fast_384:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_384; // ED NOP (0)
finish_384:
    board_finish_slice(b,pins,elapsed,384); return elapsed;
fast_385:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_385; // ED NOP (0)
finish_385:
    board_finish_slice(b,pins,elapsed,385); return elapsed;
fast_386:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_386; // ED NOP (0)
finish_386:
    board_finish_slice(b,pins,elapsed,386); return elapsed;
fast_387:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_387; // ED NOP (0)
finish_387:
    board_finish_slice(b,pins,elapsed,387); return elapsed;
fast_388:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_388; // ED NOP (0)
finish_388:
    board_finish_slice(b,pins,elapsed,388); return elapsed;
fast_389:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_389; // ED NOP (0)
finish_389:
    board_finish_slice(b,pins,elapsed,389); return elapsed;
fast_390:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_390; // ED NOP (0)
finish_390:
    board_finish_slice(b,pins,elapsed,390); return elapsed;
fast_391:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_391; // ED NOP (0)
finish_391:
    board_finish_slice(b,pins,elapsed,391); return elapsed;
fast_392:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_392; // ED NOP (0)
finish_392:
    board_finish_slice(b,pins,elapsed,392); return elapsed;
fast_393:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_393; // ED NOP (0)
finish_393:
    board_finish_slice(b,pins,elapsed,393); return elapsed;
fast_394:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_394; // ED NOP (0)
finish_394:
    board_finish_slice(b,pins,elapsed,394); return elapsed;
fast_395:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_395; // ED NOP (0)
finish_395:
    board_finish_slice(b,pins,elapsed,395); return elapsed;
fast_396:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_396; // ED NOP (0)
finish_396:
    board_finish_slice(b,pins,elapsed,396); return elapsed;
fast_397:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_397; // ED NOP (0)
finish_397:
    board_finish_slice(b,pins,elapsed,397); return elapsed;
fast_398:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_398; // ED NOP (0)
finish_398:
    board_finish_slice(b,pins,elapsed,398); return elapsed;
fast_399:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_399; // ED NOP (0)
finish_399:
    board_finish_slice(b,pins,elapsed,399); return elapsed;
fast_400:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_400; // ED NOP (0)
finish_400:
    board_finish_slice(b,pins,elapsed,400); return elapsed;
fast_401:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_401; // ED NOP (0)
finish_401:
    board_finish_slice(b,pins,elapsed,401); return elapsed;
fast_402:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_402; // ED NOP (0)
finish_402:
    board_finish_slice(b,pins,elapsed,402); return elapsed;
fast_403:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_403; // ED NOP (0)
finish_403:
    board_finish_slice(b,pins,elapsed,403); return elapsed;
fast_404:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_404; // ED NOP (0)
finish_404:
    board_finish_slice(b,pins,elapsed,404); return elapsed;
fast_405:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_405; // ED NOP (0)
finish_405:
    board_finish_slice(b,pins,elapsed,405); return elapsed;
fast_406:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_406; // ED NOP (0)
finish_406:
    board_finish_slice(b,pins,elapsed,406); return elapsed;
fast_407:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_407; // ED NOP (0)
finish_407:
    board_finish_slice(b,pins,elapsed,407); return elapsed;
fast_408:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_408; // ED NOP (0)
finish_408:
    board_finish_slice(b,pins,elapsed,408); return elapsed;
fast_409:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_409; // ED NOP (0)
finish_409:
    board_finish_slice(b,pins,elapsed,409); return elapsed;
fast_410:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_410; // ED NOP (0)
finish_410:
    board_finish_slice(b,pins,elapsed,410); return elapsed;
fast_411:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_411; // ED NOP (0)
finish_411:
    board_finish_slice(b,pins,elapsed,411); return elapsed;
fast_412:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_412; // ED NOP (0)
finish_412:
    board_finish_slice(b,pins,elapsed,412); return elapsed;
fast_413:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_413; // ED NOP (0)
finish_413:
    board_finish_slice(b,pins,elapsed,413); return elapsed;
fast_414:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_414; // ED NOP (0)
finish_414:
    board_finish_slice(b,pins,elapsed,414); return elapsed;
fast_415:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_415; // ED NOP (0)
finish_415:
    board_finish_slice(b,pins,elapsed,415); return elapsed;
fast_416:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1444; // LDI (0)
fast_417:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1452; // CPI (0)
fast_418:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1460; // INI (0)
fast_419:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1468; // OUTI (0)
fast_420:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_420; // ED NOP (0)
finish_420:
    board_finish_slice(b,pins,elapsed,420); return elapsed;
fast_421:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_421; // ED NOP (0)
finish_421:
    board_finish_slice(b,pins,elapsed,421); return elapsed;
fast_422:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_422; // ED NOP (0)
finish_422:
    board_finish_slice(b,pins,elapsed,422); return elapsed;
fast_423:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_423; // ED NOP (0)
finish_423:
    board_finish_slice(b,pins,elapsed,423); return elapsed;
fast_424:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1476; // LDD (0)
fast_425:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1484; // CPD (0)
fast_426:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1492; // IND (0)
fast_427:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1500; // OUTD (0)
fast_428:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_428; // ED NOP (0)
finish_428:
    board_finish_slice(b,pins,elapsed,428); return elapsed;
fast_429:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_429; // ED NOP (0)
finish_429:
    board_finish_slice(b,pins,elapsed,429); return elapsed;
fast_430:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_430; // ED NOP (0)
finish_430:
    board_finish_slice(b,pins,elapsed,430); return elapsed;
fast_431:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_431; // ED NOP (0)
finish_431:
    board_finish_slice(b,pins,elapsed,431); return elapsed;
fast_432:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1508; // LDIR (0)
fast_433:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1521; // CPIR (0)
fast_434:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1534; // INIR (0)
fast_435:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1547; // OTIR (0)
fast_436:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_436; // ED NOP (0)
finish_436:
    board_finish_slice(b,pins,elapsed,436); return elapsed;
fast_437:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_437; // ED NOP (0)
finish_437:
    board_finish_slice(b,pins,elapsed,437); return elapsed;
fast_438:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_438; // ED NOP (0)
finish_438:
    board_finish_slice(b,pins,elapsed,438); return elapsed;
fast_439:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_439; // ED NOP (0)
finish_439:
    board_finish_slice(b,pins,elapsed,439); return elapsed;
fast_440:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1560; // LDDR (0)
fast_441:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1573; // CPDR (0)
fast_442:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1586; // INDR (0)
fast_443:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1599; // OTDR (0)
fast_444:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_444; // ED NOP (0)
finish_444:
    board_finish_slice(b,pins,elapsed,444); return elapsed;
fast_445:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_445; // ED NOP (0)
finish_445:
    board_finish_slice(b,pins,elapsed,445); return elapsed;
fast_446:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_446; // ED NOP (0)
finish_446:
    board_finish_slice(b,pins,elapsed,446); return elapsed;
fast_447:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_447; // ED NOP (0)
finish_447:
    board_finish_slice(b,pins,elapsed,447); return elapsed;
fast_448:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_448; // ED NOP (0)
finish_448:
    board_finish_slice(b,pins,elapsed,448); return elapsed;
fast_449:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_449; // ED NOP (0)
finish_449:
    board_finish_slice(b,pins,elapsed,449); return elapsed;
fast_450:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_450; // ED NOP (0)
finish_450:
    board_finish_slice(b,pins,elapsed,450); return elapsed;
fast_451:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_451; // ED NOP (0)
finish_451:
    board_finish_slice(b,pins,elapsed,451); return elapsed;
fast_452:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_452; // ED NOP (0)
finish_452:
    board_finish_slice(b,pins,elapsed,452); return elapsed;
fast_453:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_453; // ED NOP (0)
finish_453:
    board_finish_slice(b,pins,elapsed,453); return elapsed;
fast_454:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_454; // ED NOP (0)
finish_454:
    board_finish_slice(b,pins,elapsed,454); return elapsed;
fast_455:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_455; // ED NOP (0)
finish_455:
    board_finish_slice(b,pins,elapsed,455); return elapsed;
fast_456:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_456; // ED NOP (0)
finish_456:
    board_finish_slice(b,pins,elapsed,456); return elapsed;
fast_457:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_457; // ED NOP (0)
finish_457:
    board_finish_slice(b,pins,elapsed,457); return elapsed;
fast_458:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_458; // ED NOP (0)
finish_458:
    board_finish_slice(b,pins,elapsed,458); return elapsed;
fast_459:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_459; // ED NOP (0)
finish_459:
    board_finish_slice(b,pins,elapsed,459); return elapsed;
fast_460:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_460; // ED NOP (0)
finish_460:
    board_finish_slice(b,pins,elapsed,460); return elapsed;
fast_461:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_461; // ED NOP (0)
finish_461:
    board_finish_slice(b,pins,elapsed,461); return elapsed;
fast_462:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_462; // ED NOP (0)
finish_462:
    board_finish_slice(b,pins,elapsed,462); return elapsed;
fast_463:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_463; // ED NOP (0)
finish_463:
    board_finish_slice(b,pins,elapsed,463); return elapsed;
fast_464:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_464; // ED NOP (0)
finish_464:
    board_finish_slice(b,pins,elapsed,464); return elapsed;
fast_465:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_465; // ED NOP (0)
finish_465:
    board_finish_slice(b,pins,elapsed,465); return elapsed;
fast_466:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_466; // ED NOP (0)
finish_466:
    board_finish_slice(b,pins,elapsed,466); return elapsed;
fast_467:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_467; // ED NOP (0)
finish_467:
    board_finish_slice(b,pins,elapsed,467); return elapsed;
fast_468:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_468; // ED NOP (0)
finish_468:
    board_finish_slice(b,pins,elapsed,468); return elapsed;
fast_469:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_469; // ED NOP (0)
finish_469:
    board_finish_slice(b,pins,elapsed,469); return elapsed;
fast_470:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_470; // ED NOP (0)
finish_470:
    board_finish_slice(b,pins,elapsed,470); return elapsed;
fast_471:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_471; // ED NOP (0)
finish_471:
    board_finish_slice(b,pins,elapsed,471); return elapsed;
fast_472:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_472; // ED NOP (0)
finish_472:
    board_finish_slice(b,pins,elapsed,472); return elapsed;
fast_473:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_473; // ED NOP (0)
finish_473:
    board_finish_slice(b,pins,elapsed,473); return elapsed;
fast_474:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_474; // ED NOP (0)
finish_474:
    board_finish_slice(b,pins,elapsed,474); return elapsed;
fast_475:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_475; // ED NOP (0)
finish_475:
    board_finish_slice(b,pins,elapsed,475); return elapsed;
fast_476:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_476; // ED NOP (0)
finish_476:
    board_finish_slice(b,pins,elapsed,476); return elapsed;
fast_477:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_477; // ED NOP (0)
finish_477:
    board_finish_slice(b,pins,elapsed,477); return elapsed;
fast_478:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_478; // ED NOP (0)
finish_478:
    board_finish_slice(b,pins,elapsed,478); return elapsed;
fast_479:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_479; // ED NOP (0)
finish_479:
    board_finish_slice(b,pins,elapsed,479); return elapsed;
fast_480:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_480; // ED NOP (0)
finish_480:
    board_finish_slice(b,pins,elapsed,480); return elapsed;
fast_481:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_481; // ED NOP (0)
finish_481:
    board_finish_slice(b,pins,elapsed,481); return elapsed;
fast_482:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_482; // ED NOP (0)
finish_482:
    board_finish_slice(b,pins,elapsed,482); return elapsed;
fast_483:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_483; // ED NOP (0)
finish_483:
    board_finish_slice(b,pins,elapsed,483); return elapsed;
fast_484:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_484; // ED NOP (0)
finish_484:
    board_finish_slice(b,pins,elapsed,484); return elapsed;
fast_485:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_485; // ED NOP (0)
finish_485:
    board_finish_slice(b,pins,elapsed,485); return elapsed;
fast_486:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_486; // ED NOP (0)
finish_486:
    board_finish_slice(b,pins,elapsed,486); return elapsed;
fast_487:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_487; // ED NOP (0)
finish_487:
    board_finish_slice(b,pins,elapsed,487); return elapsed;
fast_488:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_488; // ED NOP (0)
finish_488:
    board_finish_slice(b,pins,elapsed,488); return elapsed;
fast_489:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_489; // ED NOP (0)
finish_489:
    board_finish_slice(b,pins,elapsed,489); return elapsed;
fast_490:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_490; // ED NOP (0)
finish_490:
    board_finish_slice(b,pins,elapsed,490); return elapsed;
fast_491:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_491; // ED NOP (0)
finish_491:
    board_finish_slice(b,pins,elapsed,491); return elapsed;
fast_492:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_492; // ED NOP (0)
finish_492:
    board_finish_slice(b,pins,elapsed,492); return elapsed;
fast_493:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_493; // ED NOP (0)
finish_493:
    board_finish_slice(b,pins,elapsed,493); return elapsed;
fast_494:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_494; // ED NOP (0)
finish_494:
    board_finish_slice(b,pins,elapsed,494); return elapsed;
fast_495:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_495; // ED NOP (0)
finish_495:
    board_finish_slice(b,pins,elapsed,495); return elapsed;
fast_496:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_496; // ED NOP (0)
finish_496:
    board_finish_slice(b,pins,elapsed,496); return elapsed;
fast_497:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_497; // ED NOP (0)
finish_497:
    board_finish_slice(b,pins,elapsed,497); return elapsed;
fast_498:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_498; // ED NOP (0)
finish_498:
    board_finish_slice(b,pins,elapsed,498); return elapsed;
fast_499:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_499; // ED NOP (0)
finish_499:
    board_finish_slice(b,pins,elapsed,499); return elapsed;
fast_500:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_500; // ED NOP (0)
finish_500:
    board_finish_slice(b,pins,elapsed,500); return elapsed;
fast_501:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_501; // ED NOP (0)
finish_501:
    board_finish_slice(b,pins,elapsed,501); return elapsed;
fast_502:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_502; // ED NOP (0)
finish_502:
    board_finish_slice(b,pins,elapsed,502); return elapsed;
fast_503:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_503; // ED NOP (0)
finish_503:
    board_finish_slice(b,pins,elapsed,503); return elapsed;
fast_504:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_504; // ED NOP (0)
finish_504:
    board_finish_slice(b,pins,elapsed,504); return elapsed;
fast_505:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_505; // ED NOP (0)
finish_505:
    board_finish_slice(b,pins,elapsed,505); return elapsed;
fast_506:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_506; // ED NOP (0)
finish_506:
    board_finish_slice(b,pins,elapsed,506); return elapsed;
fast_507:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_507; // ED NOP (0)
finish_507:
    board_finish_slice(b,pins,elapsed,507); return elapsed;
fast_508:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_508; // ED NOP (0)
finish_508:
    board_finish_slice(b,pins,elapsed,508); return elapsed;
fast_509:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_509; // ED NOP (0)
finish_509:
    board_finish_slice(b,pins,elapsed,509); return elapsed;
fast_510:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_510; // ED NOP (0)
finish_510:
    board_finish_slice(b,pins,elapsed,510); return elapsed;
fast_511:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_511; // ED NOP (0)
finish_511:
    board_finish_slice(b,pins,elapsed,511); return elapsed;
fast_512:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_513; // LD BC,nn (1)
fast_513:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->c=_gd();goto fast_514; // LD BC,nn (2)
fast_514:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_515; // LD BC,nn (3)
fast_515:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_516; // LD BC,nn (4)
fast_516:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->b=_gd();goto fast_517; // LD BC,nn (5)
fast_517:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_517; // LD BC,nn (6)
finish_517:
    board_finish_slice(b,pins,elapsed,517); return elapsed;
fast_518:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->bc,cpu->a);cpu->wzl=cpu->c+1;cpu->wzh=cpu->a;goto fast_519; // LD (BC),A (1)
fast_519:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_520; // LD (BC),A (2)
fast_520:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_520; // LD (BC),A (3)
finish_520:
    board_finish_slice(b,pins,elapsed,520); return elapsed;
fast_521:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_522; // INC BC (1)
fast_522:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_522; // INC BC (2)
finish_522:
    board_finish_slice(b,pins,elapsed,522); return elapsed;
fast_523:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_524; // LD B,n (1)
fast_524:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->b=_gd();goto fast_525; // LD B,n (2)
fast_525:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_525; // LD B,n (3)
finish_525:
    board_finish_slice(b,pins,elapsed,525); return elapsed;
fast_526:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_527; // ADD HL,BC (1)
fast_527:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_528; // ADD HL,BC (2)
fast_528:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_529; // ADD HL,BC (3)
fast_529:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_530; // ADD HL,BC (4)
fast_530:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_531; // ADD HL,BC (5)
fast_531:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_532; // ADD HL,BC (6)
fast_532:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_532; // ADD HL,BC (7)
finish_532:
    board_finish_slice(b,pins,elapsed,532); return elapsed;
fast_533:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->bc);goto fast_534; // LD A,(BC) (1)
fast_534:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->a=_gd();cpu->wz=cpu->bc+1;goto fast_535; // LD A,(BC) (2)
fast_535:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_535; // LD A,(BC) (3)
finish_535:
    board_finish_slice(b,pins,elapsed,535); return elapsed;
fast_536:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_537; // DEC BC (1)
fast_537:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_537; // DEC BC (2)
finish_537:
    board_finish_slice(b,pins,elapsed,537); return elapsed;
fast_538:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_539; // LD C,n (1)
fast_539:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->c=_gd();goto fast_540; // LD C,n (2)
fast_540:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_540; // LD C,n (3)
finish_540:
    board_finish_slice(b,pins,elapsed,540); return elapsed;
fast_541:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_542; // DJNZ d (1)
fast_542:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_543; // DJNZ d (2)
fast_543:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();if(--cpu->b==0){goto fast_549;};goto fast_544; // DJNZ d (3)
fast_544:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->pc+=(int8_t)cpu->dlatch;cpu->wz=cpu->pc;goto fast_545; // DJNZ d (4)
fast_545:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_546; // DJNZ d (5)
fast_546:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_547; // DJNZ d (6)
fast_547:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_548; // DJNZ d (7)
fast_548:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_549; // DJNZ d (8)
fast_549:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_549; // DJNZ d (9)
finish_549:
    board_finish_slice(b,pins,elapsed,549); return elapsed;
fast_550:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_551; // LD DE,nn (1)
fast_551:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->e=_gd();goto fast_552; // LD DE,nn (2)
fast_552:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_553; // LD DE,nn (3)
fast_553:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_554; // LD DE,nn (4)
fast_554:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->d=_gd();goto fast_555; // LD DE,nn (5)
fast_555:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_555; // LD DE,nn (6)
finish_555:
    board_finish_slice(b,pins,elapsed,555); return elapsed;
fast_556:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->de,cpu->a);cpu->wzl=cpu->e+1;cpu->wzh=cpu->a;goto fast_557; // LD (DE),A (1)
fast_557:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_558; // LD (DE),A (2)
fast_558:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_558; // LD (DE),A (3)
finish_558:
    board_finish_slice(b,pins,elapsed,558); return elapsed;
fast_559:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_560; // INC DE (1)
fast_560:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_560; // INC DE (2)
finish_560:
    board_finish_slice(b,pins,elapsed,560); return elapsed;
fast_561:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_562; // LD D,n (1)
fast_562:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->d=_gd();goto fast_563; // LD D,n (2)
fast_563:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_563; // LD D,n (3)
finish_563:
    board_finish_slice(b,pins,elapsed,563); return elapsed;
fast_564:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_565; // JR d (1)
fast_565:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();goto fast_566; // JR d (2)
fast_566:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->pc+=(int8_t)cpu->dlatch;cpu->wz=cpu->pc;goto fast_567; // JR d (3)
fast_567:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_568; // JR d (4)
fast_568:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_569; // JR d (5)
fast_569:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_570; // JR d (6)
fast_570:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_571; // JR d (7)
fast_571:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_571; // JR d (8)
finish_571:
    board_finish_slice(b,pins,elapsed,571); return elapsed;
fast_572:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_573; // ADD HL,DE (1)
fast_573:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_574; // ADD HL,DE (2)
fast_574:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_575; // ADD HL,DE (3)
fast_575:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_576; // ADD HL,DE (4)
fast_576:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_577; // ADD HL,DE (5)
fast_577:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_578; // ADD HL,DE (6)
fast_578:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_578; // ADD HL,DE (7)
finish_578:
    board_finish_slice(b,pins,elapsed,578); return elapsed;
fast_579:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->de);goto fast_580; // LD A,(DE) (1)
fast_580:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->a=_gd();cpu->wz=cpu->de+1;goto fast_581; // LD A,(DE) (2)
fast_581:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_581; // LD A,(DE) (3)
finish_581:
    board_finish_slice(b,pins,elapsed,581); return elapsed;
fast_582:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_583; // DEC DE (1)
fast_583:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_583; // DEC DE (2)
finish_583:
    board_finish_slice(b,pins,elapsed,583); return elapsed;
fast_584:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_585; // LD E,n (1)
fast_585:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->e=_gd();goto fast_586; // LD E,n (2)
fast_586:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_586; // LD E,n (3)
finish_586:
    board_finish_slice(b,pins,elapsed,586); return elapsed;
fast_587:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_588; // JR NZ,d (1)
fast_588:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();if(!(_cc_nz)){goto fast_594;};goto fast_589; // JR NZ,d (2)
fast_589:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->pc+=(int8_t)cpu->dlatch;cpu->wz=cpu->pc;goto fast_590; // JR NZ,d (3)
fast_590:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_591; // JR NZ,d (4)
fast_591:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_592; // JR NZ,d (5)
fast_592:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_593; // JR NZ,d (6)
fast_593:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_594; // JR NZ,d (7)
fast_594:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_594; // JR NZ,d (8)
finish_594:
    board_finish_slice(b,pins,elapsed,594); return elapsed;
fast_595:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_596; // LD HL,nn (1)
fast_596:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->hlx[cpu->hlx_idx].l=_gd();goto fast_597; // LD HL,nn (2)
fast_597:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_598; // LD HL,nn (3)
fast_598:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_599; // LD HL,nn (4)
fast_599:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->hlx[cpu->hlx_idx].h=_gd();goto fast_600; // LD HL,nn (5)
fast_600:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_600; // LD HL,nn (6)
finish_600:
    board_finish_slice(b,pins,elapsed,600); return elapsed;
fast_601:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_602; // LD (nn),HL (1)
fast_602:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_603; // LD (nn),HL (2)
fast_603:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_604; // LD (nn),HL (3)
fast_604:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_605; // LD (nn),HL (4)
fast_605:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();goto fast_606; // LD (nn),HL (5)
fast_606:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_607; // LD (nn),HL (6)
fast_607:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->wz++,cpu->hlx[cpu->hlx_idx].l);goto fast_608; // LD (nn),HL (7)
fast_608:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_609; // LD (nn),HL (8)
fast_609:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_610; // LD (nn),HL (9)
fast_610:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->wz,cpu->hlx[cpu->hlx_idx].h);goto fast_611; // LD (nn),HL (10)
fast_611:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_612; // LD (nn),HL (11)
fast_612:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_612; // LD (nn),HL (12)
finish_612:
    board_finish_slice(b,pins,elapsed,612); return elapsed;
fast_613:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_614; // INC HL (1)
fast_614:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_614; // INC HL (2)
finish_614:
    board_finish_slice(b,pins,elapsed,614); return elapsed;
fast_615:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_616; // LD H,n (1)
fast_616:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->hlx[cpu->hlx_idx].h=_gd();goto fast_617; // LD H,n (2)
fast_617:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_617; // LD H,n (3)
finish_617:
    board_finish_slice(b,pins,elapsed,617); return elapsed;
fast_618:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_619; // JR Z,d (1)
fast_619:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();if(!(_cc_z)){goto fast_625;};goto fast_620; // JR Z,d (2)
fast_620:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->pc+=(int8_t)cpu->dlatch;cpu->wz=cpu->pc;goto fast_621; // JR Z,d (3)
fast_621:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_622; // JR Z,d (4)
fast_622:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_623; // JR Z,d (5)
fast_623:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_624; // JR Z,d (6)
fast_624:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_625; // JR Z,d (7)
fast_625:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_625; // JR Z,d (8)
finish_625:
    board_finish_slice(b,pins,elapsed,625); return elapsed;
fast_626:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_627; // ADD HL,HL (1)
fast_627:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_628; // ADD HL,HL (2)
fast_628:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_629; // ADD HL,HL (3)
fast_629:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_630; // ADD HL,HL (4)
fast_630:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_631; // ADD HL,HL (5)
fast_631:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_632; // ADD HL,HL (6)
fast_632:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_632; // ADD HL,HL (7)
finish_632:
    board_finish_slice(b,pins,elapsed,632); return elapsed;
fast_633:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_634; // LD HL,(nn) (1)
fast_634:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_635; // LD HL,(nn) (2)
fast_635:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_636; // LD HL,(nn) (3)
fast_636:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_637; // LD HL,(nn) (4)
fast_637:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();goto fast_638; // LD HL,(nn) (5)
fast_638:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_639; // LD HL,(nn) (6)
fast_639:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->wz++);goto fast_640; // LD HL,(nn) (7)
fast_640:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->hlx[cpu->hlx_idx].l=_gd();goto fast_641; // LD HL,(nn) (8)
fast_641:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_642; // LD HL,(nn) (9)
fast_642:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->wz);goto fast_643; // LD HL,(nn) (10)
fast_643:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->hlx[cpu->hlx_idx].h=_gd();goto fast_644; // LD HL,(nn) (11)
fast_644:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_644; // LD HL,(nn) (12)
finish_644:
    board_finish_slice(b,pins,elapsed,644); return elapsed;
fast_645:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_646; // DEC HL (1)
fast_646:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_646; // DEC HL (2)
finish_646:
    board_finish_slice(b,pins,elapsed,646); return elapsed;
fast_647:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_648; // LD L,n (1)
fast_648:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->hlx[cpu->hlx_idx].l=_gd();goto fast_649; // LD L,n (2)
fast_649:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_649; // LD L,n (3)
finish_649:
    board_finish_slice(b,pins,elapsed,649); return elapsed;
fast_650:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_651; // JR NC,d (1)
fast_651:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();if(!(_cc_nc)){goto fast_657;};goto fast_652; // JR NC,d (2)
fast_652:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->pc+=(int8_t)cpu->dlatch;cpu->wz=cpu->pc;goto fast_653; // JR NC,d (3)
fast_653:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_654; // JR NC,d (4)
fast_654:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_655; // JR NC,d (5)
fast_655:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_656; // JR NC,d (6)
fast_656:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_657; // JR NC,d (7)
fast_657:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_657; // JR NC,d (8)
finish_657:
    board_finish_slice(b,pins,elapsed,657); return elapsed;
fast_658:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_659; // LD SP,nn (1)
fast_659:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->spl=_gd();goto fast_660; // LD SP,nn (2)
fast_660:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_661; // LD SP,nn (3)
fast_661:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_662; // LD SP,nn (4)
fast_662:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->sph=_gd();goto fast_663; // LD SP,nn (5)
fast_663:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_663; // LD SP,nn (6)
finish_663:
    board_finish_slice(b,pins,elapsed,663); return elapsed;
fast_664:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_665; // LD (nn),A (1)
fast_665:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_666; // LD (nn),A (2)
fast_666:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_667; // LD (nn),A (3)
fast_667:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_668; // LD (nn),A (4)
fast_668:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();goto fast_669; // LD (nn),A (5)
fast_669:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_670; // LD (nn),A (6)
fast_670:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->wz++,cpu->a);cpu->wzh=cpu->a;goto fast_671; // LD (nn),A (7)
fast_671:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_672; // LD (nn),A (8)
fast_672:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_672; // LD (nn),A (9)
finish_672:
    board_finish_slice(b,pins,elapsed,672); return elapsed;
fast_673:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_674; // INC SP (1)
fast_674:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_674; // INC SP (2)
finish_674:
    board_finish_slice(b,pins,elapsed,674); return elapsed;
fast_675:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->addr);goto fast_676; // INC (HL) (1)
fast_676:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();cpu->dlatch=_z80_inc8(cpu,cpu->dlatch);goto fast_677; // INC (HL) (2)
fast_677:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_678; // INC (HL) (3)
fast_678:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_679; // INC (HL) (4)
fast_679:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->addr,cpu->dlatch);goto fast_680; // INC (HL) (5)
fast_680:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_681; // INC (HL) (6)
fast_681:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_681; // INC (HL) (7)
finish_681:
    board_finish_slice(b,pins,elapsed,681); return elapsed;
fast_682:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->addr);goto fast_683; // DEC (HL) (1)
fast_683:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();cpu->dlatch=_z80_dec8(cpu,cpu->dlatch);goto fast_684; // DEC (HL) (2)
fast_684:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_685; // DEC (HL) (3)
fast_685:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_686; // DEC (HL) (4)
fast_686:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->addr,cpu->dlatch);goto fast_687; // DEC (HL) (5)
fast_687:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_688; // DEC (HL) (6)
fast_688:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_688; // DEC (HL) (7)
finish_688:
    board_finish_slice(b,pins,elapsed,688); return elapsed;
fast_689:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_690; // LD (HL),n (1)
fast_690:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();goto fast_691; // LD (HL),n (2)
fast_691:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_692; // LD (HL),n (3)
fast_692:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->addr,cpu->dlatch);goto fast_693; // LD (HL),n (4)
fast_693:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_694; // LD (HL),n (5)
fast_694:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_694; // LD (HL),n (6)
finish_694:
    board_finish_slice(b,pins,elapsed,694); return elapsed;
fast_695:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_696; // JR C,d (1)
fast_696:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();if(!(_cc_c)){goto fast_702;};goto fast_697; // JR C,d (2)
fast_697:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->pc+=(int8_t)cpu->dlatch;cpu->wz=cpu->pc;goto fast_698; // JR C,d (3)
fast_698:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_699; // JR C,d (4)
fast_699:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_700; // JR C,d (5)
fast_700:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_701; // JR C,d (6)
fast_701:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_702; // JR C,d (7)
fast_702:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_702; // JR C,d (8)
finish_702:
    board_finish_slice(b,pins,elapsed,702); return elapsed;
fast_703:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_704; // ADD HL,SP (1)
fast_704:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_705; // ADD HL,SP (2)
fast_705:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_706; // ADD HL,SP (3)
fast_706:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_707; // ADD HL,SP (4)
fast_707:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_708; // ADD HL,SP (5)
fast_708:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_709; // ADD HL,SP (6)
fast_709:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_709; // ADD HL,SP (7)
finish_709:
    board_finish_slice(b,pins,elapsed,709); return elapsed;
fast_710:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_711; // LD A,(nn) (1)
fast_711:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_712; // LD A,(nn) (2)
fast_712:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_713; // LD A,(nn) (3)
fast_713:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_714; // LD A,(nn) (4)
fast_714:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();goto fast_715; // LD A,(nn) (5)
fast_715:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_716; // LD A,(nn) (6)
fast_716:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->wz++);goto fast_717; // LD A,(nn) (7)
fast_717:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->a=_gd();goto fast_718; // LD A,(nn) (8)
fast_718:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_718; // LD A,(nn) (9)
finish_718:
    board_finish_slice(b,pins,elapsed,718); return elapsed;
fast_719:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_720; // DEC SP (1)
fast_720:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_720; // DEC SP (2)
finish_720:
    board_finish_slice(b,pins,elapsed,720); return elapsed;
fast_721:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_722; // LD A,n (1)
fast_722:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->a=_gd();goto fast_723; // LD A,n (2)
fast_723:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_723; // LD A,n (3)
finish_723:
    board_finish_slice(b,pins,elapsed,723); return elapsed;
fast_724:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->addr);goto fast_725; // LD B,(HL) (1)
fast_725:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->b=_gd();goto fast_726; // LD B,(HL) (2)
fast_726:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_726; // LD B,(HL) (3)
finish_726:
    board_finish_slice(b,pins,elapsed,726); return elapsed;
fast_727:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->addr);goto fast_728; // LD C,(HL) (1)
fast_728:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->c=_gd();goto fast_729; // LD C,(HL) (2)
fast_729:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_729; // LD C,(HL) (3)
finish_729:
    board_finish_slice(b,pins,elapsed,729); return elapsed;
fast_730:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->addr);goto fast_731; // LD D,(HL) (1)
fast_731:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->d=_gd();goto fast_732; // LD D,(HL) (2)
fast_732:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_732; // LD D,(HL) (3)
finish_732:
    board_finish_slice(b,pins,elapsed,732); return elapsed;
fast_733:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->addr);goto fast_734; // LD E,(HL) (1)
fast_734:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->e=_gd();goto fast_735; // LD E,(HL) (2)
fast_735:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_735; // LD E,(HL) (3)
finish_735:
    board_finish_slice(b,pins,elapsed,735); return elapsed;
fast_736:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->addr);goto fast_737; // LD H,(HL) (1)
fast_737:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->h=_gd();goto fast_738; // LD H,(HL) (2)
fast_738:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_738; // LD H,(HL) (3)
finish_738:
    board_finish_slice(b,pins,elapsed,738); return elapsed;
fast_739:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->addr);goto fast_740; // LD L,(HL) (1)
fast_740:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->l=_gd();goto fast_741; // LD L,(HL) (2)
fast_741:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_741; // LD L,(HL) (3)
finish_741:
    board_finish_slice(b,pins,elapsed,741); return elapsed;
fast_742:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->addr,cpu->b);goto fast_743; // LD (HL),B (1)
fast_743:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_744; // LD (HL),B (2)
fast_744:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_744; // LD (HL),B (3)
finish_744:
    board_finish_slice(b,pins,elapsed,744); return elapsed;
fast_745:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->addr,cpu->c);goto fast_746; // LD (HL),C (1)
fast_746:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_747; // LD (HL),C (2)
fast_747:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_747; // LD (HL),C (3)
finish_747:
    board_finish_slice(b,pins,elapsed,747); return elapsed;
fast_748:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->addr,cpu->d);goto fast_749; // LD (HL),D (1)
fast_749:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_750; // LD (HL),D (2)
fast_750:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_750; // LD (HL),D (3)
finish_750:
    board_finish_slice(b,pins,elapsed,750); return elapsed;
fast_751:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->addr,cpu->e);goto fast_752; // LD (HL),E (1)
fast_752:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_753; // LD (HL),E (2)
fast_753:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_753; // LD (HL),E (3)
finish_753:
    board_finish_slice(b,pins,elapsed,753); return elapsed;
fast_754:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->addr,cpu->h);goto fast_755; // LD (HL),H (1)
fast_755:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_756; // LD (HL),H (2)
fast_756:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_756; // LD (HL),H (3)
finish_756:
    board_finish_slice(b,pins,elapsed,756); return elapsed;
fast_757:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->addr,cpu->l);goto fast_758; // LD (HL),L (1)
fast_758:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_759; // LD (HL),L (2)
fast_759:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_759; // LD (HL),L (3)
finish_759:
    board_finish_slice(b,pins,elapsed,759); return elapsed;
fast_760:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->addr,cpu->a);goto fast_761; // LD (HL),A (1)
fast_761:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_762; // LD (HL),A (2)
fast_762:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_762; // LD (HL),A (3)
finish_762:
    board_finish_slice(b,pins,elapsed,762); return elapsed;
fast_763:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->addr);goto fast_764; // LD A,(HL) (1)
fast_764:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->a=_gd();goto fast_765; // LD A,(HL) (2)
fast_765:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_765; // LD A,(HL) (3)
finish_765:
    board_finish_slice(b,pins,elapsed,765); return elapsed;
fast_766:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->addr);goto fast_767; // ADD (HL) (1)
fast_767:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();goto fast_768; // ADD (HL) (2)
fast_768:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_add8(cpu,cpu->dlatch);pins=_z80_fetch(cpu,pins); goto finish_768; // ADD (HL) (3)
finish_768:
    board_finish_slice(b,pins,elapsed,768); return elapsed;
fast_769:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->addr);goto fast_770; // ADC (HL) (1)
fast_770:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();goto fast_771; // ADC (HL) (2)
fast_771:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_adc8(cpu,cpu->dlatch);pins=_z80_fetch(cpu,pins); goto finish_771; // ADC (HL) (3)
finish_771:
    board_finish_slice(b,pins,elapsed,771); return elapsed;
fast_772:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->addr);goto fast_773; // SUB (HL) (1)
fast_773:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();goto fast_774; // SUB (HL) (2)
fast_774:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_sub8(cpu,cpu->dlatch);pins=_z80_fetch(cpu,pins); goto finish_774; // SUB (HL) (3)
finish_774:
    board_finish_slice(b,pins,elapsed,774); return elapsed;
fast_775:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->addr);goto fast_776; // SBC (HL) (1)
fast_776:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();goto fast_777; // SBC (HL) (2)
fast_777:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_sbc8(cpu,cpu->dlatch);pins=_z80_fetch(cpu,pins); goto finish_777; // SBC (HL) (3)
finish_777:
    board_finish_slice(b,pins,elapsed,777); return elapsed;
fast_778:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->addr);goto fast_779; // AND (HL) (1)
fast_779:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();goto fast_780; // AND (HL) (2)
fast_780:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_and8(cpu,cpu->dlatch);pins=_z80_fetch(cpu,pins); goto finish_780; // AND (HL) (3)
finish_780:
    board_finish_slice(b,pins,elapsed,780); return elapsed;
fast_781:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->addr);goto fast_782; // XOR (HL) (1)
fast_782:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();goto fast_783; // XOR (HL) (2)
fast_783:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_xor8(cpu,cpu->dlatch);pins=_z80_fetch(cpu,pins); goto finish_783; // XOR (HL) (3)
finish_783:
    board_finish_slice(b,pins,elapsed,783); return elapsed;
fast_784:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->addr);goto fast_785; // OR (HL) (1)
fast_785:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();goto fast_786; // OR (HL) (2)
fast_786:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_or8(cpu,cpu->dlatch);pins=_z80_fetch(cpu,pins); goto finish_786; // OR (HL) (3)
finish_786:
    board_finish_slice(b,pins,elapsed,786); return elapsed;
fast_787:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->addr);goto fast_788; // CP (HL) (1)
fast_788:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();goto fast_789; // CP (HL) (2)
fast_789:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_cp8(cpu,cpu->dlatch);pins=_z80_fetch(cpu,pins); goto finish_789; // CP (HL) (3)
finish_789:
    board_finish_slice(b,pins,elapsed,789); return elapsed;
fast_790:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_791; // RET NZ (1)
fast_791:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->sp++);goto fast_792; // RET NZ (2)
fast_792:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_793; // RET NZ (3)
fast_793:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_794; // RET NZ (4)
fast_794:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->sp++);goto fast_795; // RET NZ (5)
fast_795:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();cpu->pc=cpu->wz;goto fast_796; // RET NZ (6)
fast_796:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_796; // RET NZ (7)
finish_796:
    board_finish_slice(b,pins,elapsed,796); return elapsed;
fast_797:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->sp++);goto fast_798; // POP BC (1)
fast_798:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->c=_gd();goto fast_799; // POP BC (2)
fast_799:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_800; // POP BC (3)
fast_800:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->sp++);goto fast_801; // POP BC (4)
fast_801:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->b=_gd();goto fast_802; // POP BC (5)
fast_802:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_802; // POP BC (6)
finish_802:
    board_finish_slice(b,pins,elapsed,802); return elapsed;
fast_803:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_804; // JP NZ,nn (1)
fast_804:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_805; // JP NZ,nn (2)
fast_805:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_806; // JP NZ,nn (3)
fast_806:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_807; // JP NZ,nn (4)
fast_807:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();if(_cc_nz){cpu->pc=cpu->wz;};goto fast_808; // JP NZ,nn (5)
fast_808:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_808; // JP NZ,nn (6)
finish_808:
    board_finish_slice(b,pins,elapsed,808); return elapsed;
fast_809:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_810; // JP nn (1)
fast_810:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_811; // JP nn (2)
fast_811:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_812; // JP nn (3)
fast_812:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_813; // JP nn (4)
fast_813:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();cpu->pc=cpu->wz;goto fast_814; // JP nn (5)
fast_814:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_814; // JP nn (6)
finish_814:
    board_finish_slice(b,pins,elapsed,814); return elapsed;
fast_815:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_816; // CALL NZ,nn (1)
fast_816:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_817; // CALL NZ,nn (2)
fast_817:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_818; // CALL NZ,nn (3)
fast_818:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_819; // CALL NZ,nn (4)
fast_819:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();if (!_cc_nz){goto fast_827;};goto fast_820; // CALL NZ,nn (5)
fast_820:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_821; // CALL NZ,nn (6)
fast_821:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_822; // CALL NZ,nn (7)
fast_822:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pch);goto fast_823; // CALL NZ,nn (8)
fast_823:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_824; // CALL NZ,nn (9)
fast_824:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_825; // CALL NZ,nn (10)
fast_825:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pcl);cpu->pc=cpu->wz;goto fast_826; // CALL NZ,nn (11)
fast_826:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_827; // CALL NZ,nn (12)
fast_827:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_827; // CALL NZ,nn (13)
finish_827:
    board_finish_slice(b,pins,elapsed,827); return elapsed;
fast_828:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_829; // PUSH BC (1)
fast_829:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->b);goto fast_830; // PUSH BC (2)
fast_830:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_831; // PUSH BC (3)
fast_831:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_832; // PUSH BC (4)
fast_832:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->c);goto fast_833; // PUSH BC (5)
fast_833:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_834; // PUSH BC (6)
fast_834:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_834; // PUSH BC (7)
finish_834:
    board_finish_slice(b,pins,elapsed,834); return elapsed;
fast_835:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_836; // ADD n (1)
fast_836:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();goto fast_837; // ADD n (2)
fast_837:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_add8(cpu,cpu->dlatch);pins=_z80_fetch(cpu,pins); goto finish_837; // ADD n (3)
finish_837:
    board_finish_slice(b,pins,elapsed,837); return elapsed;
fast_838:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_839; // RST 0h (1)
fast_839:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pch);goto fast_840; // RST 0h (2)
fast_840:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_841; // RST 0h (3)
fast_841:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_842; // RST 0h (4)
fast_842:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pcl);cpu->wz=0x00;cpu->pc=cpu->wz;goto fast_843; // RST 0h (5)
fast_843:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_844; // RST 0h (6)
fast_844:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_844; // RST 0h (7)
finish_844:
    board_finish_slice(b,pins,elapsed,844); return elapsed;
fast_845:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_846; // RET Z (1)
fast_846:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->sp++);goto fast_847; // RET Z (2)
fast_847:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_848; // RET Z (3)
fast_848:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_849; // RET Z (4)
fast_849:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->sp++);goto fast_850; // RET Z (5)
fast_850:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();cpu->pc=cpu->wz;goto fast_851; // RET Z (6)
fast_851:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_851; // RET Z (7)
finish_851:
    board_finish_slice(b,pins,elapsed,851); return elapsed;
fast_852:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->sp++);goto fast_853; // RET (1)
fast_853:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_854; // RET (2)
fast_854:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_855; // RET (3)
fast_855:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->sp++);goto fast_856; // RET (4)
fast_856:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();cpu->pc=cpu->wz;goto fast_857; // RET (5)
fast_857:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_857; // RET (6)
finish_857:
    board_finish_slice(b,pins,elapsed,857); return elapsed;
fast_858:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_859; // JP Z,nn (1)
fast_859:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_860; // JP Z,nn (2)
fast_860:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_861; // JP Z,nn (3)
fast_861:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_862; // JP Z,nn (4)
fast_862:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();if(_cc_z){cpu->pc=cpu->wz;};goto fast_863; // JP Z,nn (5)
fast_863:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_863; // JP Z,nn (6)
finish_863:
    board_finish_slice(b,pins,elapsed,863); return elapsed;
fast_864:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_865; // CALL Z,nn (1)
fast_865:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_866; // CALL Z,nn (2)
fast_866:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_867; // CALL Z,nn (3)
fast_867:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_868; // CALL Z,nn (4)
fast_868:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();if (!_cc_z){goto fast_876;};goto fast_869; // CALL Z,nn (5)
fast_869:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_870; // CALL Z,nn (6)
fast_870:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_871; // CALL Z,nn (7)
fast_871:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pch);goto fast_872; // CALL Z,nn (8)
fast_872:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_873; // CALL Z,nn (9)
fast_873:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_874; // CALL Z,nn (10)
fast_874:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pcl);cpu->pc=cpu->wz;goto fast_875; // CALL Z,nn (11)
fast_875:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_876; // CALL Z,nn (12)
fast_876:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_876; // CALL Z,nn (13)
finish_876:
    board_finish_slice(b,pins,elapsed,876); return elapsed;
fast_877:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_878; // CALL nn (1)
fast_878:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_879; // CALL nn (2)
fast_879:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_880; // CALL nn (3)
fast_880:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_881; // CALL nn (4)
fast_881:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();goto fast_882; // CALL nn (5)
fast_882:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_883; // CALL nn (6)
fast_883:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_884; // CALL nn (7)
fast_884:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pch);goto fast_885; // CALL nn (8)
fast_885:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_886; // CALL nn (9)
fast_886:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_887; // CALL nn (10)
fast_887:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pcl);cpu->pc=cpu->wz;goto fast_888; // CALL nn (11)
fast_888:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_889; // CALL nn (12)
fast_889:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_889; // CALL nn (13)
finish_889:
    board_finish_slice(b,pins,elapsed,889); return elapsed;
fast_890:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_891; // ADC n (1)
fast_891:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();goto fast_892; // ADC n (2)
fast_892:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_adc8(cpu,cpu->dlatch);pins=_z80_fetch(cpu,pins); goto finish_892; // ADC n (3)
finish_892:
    board_finish_slice(b,pins,elapsed,892); return elapsed;
fast_893:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_894; // RST 8h (1)
fast_894:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pch);goto fast_895; // RST 8h (2)
fast_895:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_896; // RST 8h (3)
fast_896:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_897; // RST 8h (4)
fast_897:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pcl);cpu->wz=0x08;cpu->pc=cpu->wz;goto fast_898; // RST 8h (5)
fast_898:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_899; // RST 8h (6)
fast_899:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_899; // RST 8h (7)
finish_899:
    board_finish_slice(b,pins,elapsed,899); return elapsed;
fast_900:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_901; // RET NC (1)
fast_901:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->sp++);goto fast_902; // RET NC (2)
fast_902:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_903; // RET NC (3)
fast_903:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_904; // RET NC (4)
fast_904:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->sp++);goto fast_905; // RET NC (5)
fast_905:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();cpu->pc=cpu->wz;goto fast_906; // RET NC (6)
fast_906:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_906; // RET NC (7)
finish_906:
    board_finish_slice(b,pins,elapsed,906); return elapsed;
fast_907:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->sp++);goto fast_908; // POP DE (1)
fast_908:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->e=_gd();goto fast_909; // POP DE (2)
fast_909:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_910; // POP DE (3)
fast_910:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->sp++);goto fast_911; // POP DE (4)
fast_911:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->d=_gd();goto fast_912; // POP DE (5)
fast_912:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_912; // POP DE (6)
finish_912:
    board_finish_slice(b,pins,elapsed,912); return elapsed;
fast_913:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_914; // JP NC,nn (1)
fast_914:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_915; // JP NC,nn (2)
fast_915:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_916; // JP NC,nn (3)
fast_916:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_917; // JP NC,nn (4)
fast_917:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();if(_cc_nc){cpu->pc=cpu->wz;};goto fast_918; // JP NC,nn (5)
fast_918:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_918; // JP NC,nn (6)
finish_918:
    board_finish_slice(b,pins,elapsed,918); return elapsed;
fast_919:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_920; // OUT (n),A (1)
fast_920:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();cpu->wzh=cpu->a;goto fast_921; // OUT (n),A (2)
fast_921:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_922; // OUT (n),A (3)
fast_922:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _iowrite(cpu->wz,cpu->a);goto fast_923; // OUT (n),A (4)
fast_923:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();cpu->wzl++;goto fast_924; // OUT (n),A (5)
fast_924:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_925; // OUT (n),A (6)
fast_925:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_925; // OUT (n),A (7)
finish_925:
    board_finish_slice(b,pins,elapsed,925); return elapsed;
fast_926:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_927; // CALL NC,nn (1)
fast_927:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_928; // CALL NC,nn (2)
fast_928:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_929; // CALL NC,nn (3)
fast_929:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_930; // CALL NC,nn (4)
fast_930:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();if (!_cc_nc){goto fast_938;};goto fast_931; // CALL NC,nn (5)
fast_931:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_932; // CALL NC,nn (6)
fast_932:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_933; // CALL NC,nn (7)
fast_933:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pch);goto fast_934; // CALL NC,nn (8)
fast_934:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_935; // CALL NC,nn (9)
fast_935:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_936; // CALL NC,nn (10)
fast_936:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pcl);cpu->pc=cpu->wz;goto fast_937; // CALL NC,nn (11)
fast_937:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_938; // CALL NC,nn (12)
fast_938:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_938; // CALL NC,nn (13)
finish_938:
    board_finish_slice(b,pins,elapsed,938); return elapsed;
fast_939:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_940; // PUSH DE (1)
fast_940:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->d);goto fast_941; // PUSH DE (2)
fast_941:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_942; // PUSH DE (3)
fast_942:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_943; // PUSH DE (4)
fast_943:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->e);goto fast_944; // PUSH DE (5)
fast_944:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_945; // PUSH DE (6)
fast_945:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_945; // PUSH DE (7)
finish_945:
    board_finish_slice(b,pins,elapsed,945); return elapsed;
fast_946:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_947; // SUB n (1)
fast_947:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();goto fast_948; // SUB n (2)
fast_948:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_sub8(cpu,cpu->dlatch);pins=_z80_fetch(cpu,pins); goto finish_948; // SUB n (3)
finish_948:
    board_finish_slice(b,pins,elapsed,948); return elapsed;
fast_949:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_950; // RST 10h (1)
fast_950:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pch);goto fast_951; // RST 10h (2)
fast_951:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_952; // RST 10h (3)
fast_952:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_953; // RST 10h (4)
fast_953:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pcl);cpu->wz=0x10;cpu->pc=cpu->wz;goto fast_954; // RST 10h (5)
fast_954:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_955; // RST 10h (6)
fast_955:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_955; // RST 10h (7)
finish_955:
    board_finish_slice(b,pins,elapsed,955); return elapsed;
fast_956:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_957; // RET C (1)
fast_957:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->sp++);goto fast_958; // RET C (2)
fast_958:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_959; // RET C (3)
fast_959:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_960; // RET C (4)
fast_960:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->sp++);goto fast_961; // RET C (5)
fast_961:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();cpu->pc=cpu->wz;goto fast_962; // RET C (6)
fast_962:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_962; // RET C (7)
finish_962:
    board_finish_slice(b,pins,elapsed,962); return elapsed;
fast_963:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_964; // JP C,nn (1)
fast_964:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_965; // JP C,nn (2)
fast_965:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_966; // JP C,nn (3)
fast_966:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_967; // JP C,nn (4)
fast_967:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();if(_cc_c){cpu->pc=cpu->wz;};goto fast_968; // JP C,nn (5)
fast_968:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_968; // JP C,nn (6)
finish_968:
    board_finish_slice(b,pins,elapsed,968); return elapsed;
fast_969:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_970; // IN A,(n) (1)
fast_970:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();cpu->wzh=cpu->a;goto fast_971; // IN A,(n) (2)
fast_971:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_972; // IN A,(n) (3)
fast_972:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_973; // IN A,(n) (4)
fast_973:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_ioread(cpu->wz++);goto fast_974; // IN A,(n) (5)
fast_974:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->a=_gd();goto fast_975; // IN A,(n) (6)
fast_975:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_975; // IN A,(n) (7)
finish_975:
    board_finish_slice(b,pins,elapsed,975); return elapsed;
fast_976:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_977; // CALL C,nn (1)
fast_977:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_978; // CALL C,nn (2)
fast_978:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_979; // CALL C,nn (3)
fast_979:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_980; // CALL C,nn (4)
fast_980:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();if (!_cc_c){goto fast_988;};goto fast_981; // CALL C,nn (5)
fast_981:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_982; // CALL C,nn (6)
fast_982:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_983; // CALL C,nn (7)
fast_983:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pch);goto fast_984; // CALL C,nn (8)
fast_984:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_985; // CALL C,nn (9)
fast_985:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_986; // CALL C,nn (10)
fast_986:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pcl);cpu->pc=cpu->wz;goto fast_987; // CALL C,nn (11)
fast_987:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_988; // CALL C,nn (12)
fast_988:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_988; // CALL C,nn (13)
finish_988:
    board_finish_slice(b,pins,elapsed,988); return elapsed;
fast_989:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_990; // SBC n (1)
fast_990:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();goto fast_991; // SBC n (2)
fast_991:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_sbc8(cpu,cpu->dlatch);pins=_z80_fetch(cpu,pins); goto finish_991; // SBC n (3)
finish_991:
    board_finish_slice(b,pins,elapsed,991); return elapsed;
fast_992:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_993; // RST 18h (1)
fast_993:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pch);goto fast_994; // RST 18h (2)
fast_994:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_995; // RST 18h (3)
fast_995:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_996; // RST 18h (4)
fast_996:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pcl);cpu->wz=0x18;cpu->pc=cpu->wz;goto fast_997; // RST 18h (5)
fast_997:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_998; // RST 18h (6)
fast_998:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_998; // RST 18h (7)
finish_998:
    board_finish_slice(b,pins,elapsed,998); return elapsed;
fast_999:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1000; // RET PO (1)
fast_1000:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->sp++);goto fast_1001; // RET PO (2)
fast_1001:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_1002; // RET PO (3)
fast_1002:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1003; // RET PO (4)
fast_1003:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->sp++);goto fast_1004; // RET PO (5)
fast_1004:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();cpu->pc=cpu->wz;goto fast_1005; // RET PO (6)
fast_1005:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1005; // RET PO (7)
finish_1005:
    board_finish_slice(b,pins,elapsed,1005); return elapsed;
fast_1006:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->sp++);goto fast_1007; // POP HL (1)
fast_1007:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->hlx[cpu->hlx_idx].l=_gd();goto fast_1008; // POP HL (2)
fast_1008:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1009; // POP HL (3)
fast_1009:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->sp++);goto fast_1010; // POP HL (4)
fast_1010:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->hlx[cpu->hlx_idx].h=_gd();goto fast_1011; // POP HL (5)
fast_1011:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1011; // POP HL (6)
finish_1011:
    board_finish_slice(b,pins,elapsed,1011); return elapsed;
fast_1012:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1013; // JP PO,nn (1)
fast_1013:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_1014; // JP PO,nn (2)
fast_1014:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1015; // JP PO,nn (3)
fast_1015:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1016; // JP PO,nn (4)
fast_1016:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();if(_cc_po){cpu->pc=cpu->wz;};goto fast_1017; // JP PO,nn (5)
fast_1017:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1017; // JP PO,nn (6)
finish_1017:
    board_finish_slice(b,pins,elapsed,1017); return elapsed;
fast_1018:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->sp);goto fast_1019; // EX (SP),HL (1)
fast_1019:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_1020; // EX (SP),HL (2)
fast_1020:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1021; // EX (SP),HL (3)
fast_1021:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->sp+1);goto fast_1022; // EX (SP),HL (4)
fast_1022:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();goto fast_1023; // EX (SP),HL (5)
fast_1023:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1024; // EX (SP),HL (6)
fast_1024:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1025; // EX (SP),HL (7)
fast_1025:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->sp+1,cpu->hlx[cpu->hlx_idx].h);goto fast_1026; // EX (SP),HL (8)
fast_1026:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1027; // EX (SP),HL (9)
fast_1027:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1028; // EX (SP),HL (10)
fast_1028:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->sp,cpu->hlx[cpu->hlx_idx].l);cpu->hlx[cpu->hlx_idx].hl=cpu->wz;goto fast_1029; // EX (SP),HL (11)
fast_1029:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1030; // EX (SP),HL (12)
fast_1030:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1031; // EX (SP),HL (13)
fast_1031:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1032; // EX (SP),HL (14)
fast_1032:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1032; // EX (SP),HL (15)
finish_1032:
    board_finish_slice(b,pins,elapsed,1032); return elapsed;
fast_1033:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1034; // CALL PO,nn (1)
fast_1034:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_1035; // CALL PO,nn (2)
fast_1035:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1036; // CALL PO,nn (3)
fast_1036:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1037; // CALL PO,nn (4)
fast_1037:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();if (!_cc_po){goto fast_1045;};goto fast_1038; // CALL PO,nn (5)
fast_1038:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1039; // CALL PO,nn (6)
fast_1039:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1040; // CALL PO,nn (7)
fast_1040:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pch);goto fast_1041; // CALL PO,nn (8)
fast_1041:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1042; // CALL PO,nn (9)
fast_1042:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1043; // CALL PO,nn (10)
fast_1043:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pcl);cpu->pc=cpu->wz;goto fast_1044; // CALL PO,nn (11)
fast_1044:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1045; // CALL PO,nn (12)
fast_1045:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1045; // CALL PO,nn (13)
finish_1045:
    board_finish_slice(b,pins,elapsed,1045); return elapsed;
fast_1046:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1047; // PUSH HL (1)
fast_1047:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->hlx[cpu->hlx_idx].h);goto fast_1048; // PUSH HL (2)
fast_1048:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1049; // PUSH HL (3)
fast_1049:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1050; // PUSH HL (4)
fast_1050:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->hlx[cpu->hlx_idx].l);goto fast_1051; // PUSH HL (5)
fast_1051:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1052; // PUSH HL (6)
fast_1052:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1052; // PUSH HL (7)
finish_1052:
    board_finish_slice(b,pins,elapsed,1052); return elapsed;
fast_1053:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1054; // AND n (1)
fast_1054:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();goto fast_1055; // AND n (2)
fast_1055:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_and8(cpu,cpu->dlatch);pins=_z80_fetch(cpu,pins); goto finish_1055; // AND n (3)
finish_1055:
    board_finish_slice(b,pins,elapsed,1055); return elapsed;
fast_1056:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1057; // RST 20h (1)
fast_1057:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pch);goto fast_1058; // RST 20h (2)
fast_1058:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1059; // RST 20h (3)
fast_1059:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1060; // RST 20h (4)
fast_1060:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pcl);cpu->wz=0x20;cpu->pc=cpu->wz;goto fast_1061; // RST 20h (5)
fast_1061:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1062; // RST 20h (6)
fast_1062:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1062; // RST 20h (7)
finish_1062:
    board_finish_slice(b,pins,elapsed,1062); return elapsed;
fast_1063:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1064; // RET PE (1)
fast_1064:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->sp++);goto fast_1065; // RET PE (2)
fast_1065:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_1066; // RET PE (3)
fast_1066:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1067; // RET PE (4)
fast_1067:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->sp++);goto fast_1068; // RET PE (5)
fast_1068:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();cpu->pc=cpu->wz;goto fast_1069; // RET PE (6)
fast_1069:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1069; // RET PE (7)
finish_1069:
    board_finish_slice(b,pins,elapsed,1069); return elapsed;
fast_1070:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1071; // JP PE,nn (1)
fast_1071:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_1072; // JP PE,nn (2)
fast_1072:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1073; // JP PE,nn (3)
fast_1073:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1074; // JP PE,nn (4)
fast_1074:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();if(_cc_pe){cpu->pc=cpu->wz;};goto fast_1075; // JP PE,nn (5)
fast_1075:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1075; // JP PE,nn (6)
finish_1075:
    board_finish_slice(b,pins,elapsed,1075); return elapsed;
fast_1076:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1077; // CALL PE,nn (1)
fast_1077:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_1078; // CALL PE,nn (2)
fast_1078:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1079; // CALL PE,nn (3)
fast_1079:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1080; // CALL PE,nn (4)
fast_1080:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();if (!_cc_pe){goto fast_1088;};goto fast_1081; // CALL PE,nn (5)
fast_1081:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1082; // CALL PE,nn (6)
fast_1082:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1083; // CALL PE,nn (7)
fast_1083:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pch);goto fast_1084; // CALL PE,nn (8)
fast_1084:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1085; // CALL PE,nn (9)
fast_1085:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1086; // CALL PE,nn (10)
fast_1086:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pcl);cpu->pc=cpu->wz;goto fast_1087; // CALL PE,nn (11)
fast_1087:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1088; // CALL PE,nn (12)
fast_1088:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1088; // CALL PE,nn (13)
finish_1088:
    board_finish_slice(b,pins,elapsed,1088); return elapsed;
fast_1089:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1090; // XOR n (1)
fast_1090:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();goto fast_1091; // XOR n (2)
fast_1091:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_xor8(cpu,cpu->dlatch);pins=_z80_fetch(cpu,pins); goto finish_1091; // XOR n (3)
finish_1091:
    board_finish_slice(b,pins,elapsed,1091); return elapsed;
fast_1092:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1093; // RST 28h (1)
fast_1093:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pch);goto fast_1094; // RST 28h (2)
fast_1094:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1095; // RST 28h (3)
fast_1095:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1096; // RST 28h (4)
fast_1096:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pcl);cpu->wz=0x28;cpu->pc=cpu->wz;goto fast_1097; // RST 28h (5)
fast_1097:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1098; // RST 28h (6)
fast_1098:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1098; // RST 28h (7)
finish_1098:
    board_finish_slice(b,pins,elapsed,1098); return elapsed;
fast_1099:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1100; // RET P (1)
fast_1100:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->sp++);goto fast_1101; // RET P (2)
fast_1101:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_1102; // RET P (3)
fast_1102:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1103; // RET P (4)
fast_1103:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->sp++);goto fast_1104; // RET P (5)
fast_1104:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();cpu->pc=cpu->wz;goto fast_1105; // RET P (6)
fast_1105:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1105; // RET P (7)
finish_1105:
    board_finish_slice(b,pins,elapsed,1105); return elapsed;
fast_1106:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->sp++);goto fast_1107; // POP AF (1)
fast_1107:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->f=_gd();goto fast_1108; // POP AF (2)
fast_1108:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1109; // POP AF (3)
fast_1109:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->sp++);goto fast_1110; // POP AF (4)
fast_1110:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->a=_gd();goto fast_1111; // POP AF (5)
fast_1111:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1111; // POP AF (6)
finish_1111:
    board_finish_slice(b,pins,elapsed,1111); return elapsed;
fast_1112:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1113; // JP P,nn (1)
fast_1113:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_1114; // JP P,nn (2)
fast_1114:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1115; // JP P,nn (3)
fast_1115:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1116; // JP P,nn (4)
fast_1116:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();if(_cc_p){cpu->pc=cpu->wz;};goto fast_1117; // JP P,nn (5)
fast_1117:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1117; // JP P,nn (6)
finish_1117:
    board_finish_slice(b,pins,elapsed,1117); return elapsed;
fast_1118:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1119; // CALL P,nn (1)
fast_1119:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_1120; // CALL P,nn (2)
fast_1120:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1121; // CALL P,nn (3)
fast_1121:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1122; // CALL P,nn (4)
fast_1122:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();if (!_cc_p){goto fast_1130;};goto fast_1123; // CALL P,nn (5)
fast_1123:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1124; // CALL P,nn (6)
fast_1124:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1125; // CALL P,nn (7)
fast_1125:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pch);goto fast_1126; // CALL P,nn (8)
fast_1126:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1127; // CALL P,nn (9)
fast_1127:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1128; // CALL P,nn (10)
fast_1128:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pcl);cpu->pc=cpu->wz;goto fast_1129; // CALL P,nn (11)
fast_1129:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1130; // CALL P,nn (12)
fast_1130:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1130; // CALL P,nn (13)
finish_1130:
    board_finish_slice(b,pins,elapsed,1130); return elapsed;
fast_1131:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1132; // PUSH AF (1)
fast_1132:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->a);goto fast_1133; // PUSH AF (2)
fast_1133:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1134; // PUSH AF (3)
fast_1134:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1135; // PUSH AF (4)
fast_1135:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->f);goto fast_1136; // PUSH AF (5)
fast_1136:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1137; // PUSH AF (6)
fast_1137:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1137; // PUSH AF (7)
finish_1137:
    board_finish_slice(b,pins,elapsed,1137); return elapsed;
fast_1138:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1139; // OR n (1)
fast_1139:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();goto fast_1140; // OR n (2)
fast_1140:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_or8(cpu,cpu->dlatch);pins=_z80_fetch(cpu,pins); goto finish_1140; // OR n (3)
finish_1140:
    board_finish_slice(b,pins,elapsed,1140); return elapsed;
fast_1141:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1142; // RST 30h (1)
fast_1142:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pch);goto fast_1143; // RST 30h (2)
fast_1143:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1144; // RST 30h (3)
fast_1144:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1145; // RST 30h (4)
fast_1145:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pcl);cpu->wz=0x30;cpu->pc=cpu->wz;goto fast_1146; // RST 30h (5)
fast_1146:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1147; // RST 30h (6)
fast_1147:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1147; // RST 30h (7)
finish_1147:
    board_finish_slice(b,pins,elapsed,1147); return elapsed;
fast_1148:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1149; // RET M (1)
fast_1149:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->sp++);goto fast_1150; // RET M (2)
fast_1150:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_1151; // RET M (3)
fast_1151:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1152; // RET M (4)
fast_1152:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->sp++);goto fast_1153; // RET M (5)
fast_1153:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();cpu->pc=cpu->wz;goto fast_1154; // RET M (6)
fast_1154:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1154; // RET M (7)
finish_1154:
    board_finish_slice(b,pins,elapsed,1154); return elapsed;
fast_1155:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1156; // LD SP,HL (1)
fast_1156:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1156; // LD SP,HL (2)
finish_1156:
    board_finish_slice(b,pins,elapsed,1156); return elapsed;
fast_1157:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1158; // JP M,nn (1)
fast_1158:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_1159; // JP M,nn (2)
fast_1159:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1160; // JP M,nn (3)
fast_1160:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1161; // JP M,nn (4)
fast_1161:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();if(_cc_m){cpu->pc=cpu->wz;};goto fast_1162; // JP M,nn (5)
fast_1162:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1162; // JP M,nn (6)
finish_1162:
    board_finish_slice(b,pins,elapsed,1162); return elapsed;
fast_1163:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1164; // CALL M,nn (1)
fast_1164:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_1165; // CALL M,nn (2)
fast_1165:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1166; // CALL M,nn (3)
fast_1166:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1167; // CALL M,nn (4)
fast_1167:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();if (!_cc_m){goto fast_1175;};goto fast_1168; // CALL M,nn (5)
fast_1168:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1169; // CALL M,nn (6)
fast_1169:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1170; // CALL M,nn (7)
fast_1170:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pch);goto fast_1171; // CALL M,nn (8)
fast_1171:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1172; // CALL M,nn (9)
fast_1172:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1173; // CALL M,nn (10)
fast_1173:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pcl);cpu->pc=cpu->wz;goto fast_1174; // CALL M,nn (11)
fast_1174:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1175; // CALL M,nn (12)
fast_1175:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1175; // CALL M,nn (13)
finish_1175:
    board_finish_slice(b,pins,elapsed,1175); return elapsed;
fast_1176:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1177; // CP n (1)
fast_1177:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();goto fast_1178; // CP n (2)
fast_1178:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_cp8(cpu,cpu->dlatch);pins=_z80_fetch(cpu,pins); goto finish_1178; // CP n (3)
finish_1178:
    board_finish_slice(b,pins,elapsed,1178); return elapsed;
fast_1179:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1180; // RST 38h (1)
fast_1180:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pch);goto fast_1181; // RST 38h (2)
fast_1181:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1182; // RST 38h (3)
fast_1182:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1183; // RST 38h (4)
fast_1183:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pcl);cpu->wz=0x38;cpu->pc=cpu->wz;goto fast_1184; // RST 38h (5)
fast_1184:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1185; // RST 38h (6)
fast_1185:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1185; // RST 38h (7)
finish_1185:
    board_finish_slice(b,pins,elapsed,1185); return elapsed;
fast_1186:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1187; // IN B,(C) (1)
fast_1187:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_ioread(cpu->bc);goto fast_1188; // IN B,(C) (2)
fast_1188:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();cpu->wz=cpu->bc+1;goto fast_1189; // IN B,(C) (3)
fast_1189:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->b=_z80_in(cpu,cpu->dlatch);pins=_z80_fetch(cpu,pins); goto finish_1189; // IN B,(C) (4)
finish_1189:
    board_finish_slice(b,pins,elapsed,1189); return elapsed;
fast_1190:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _iowrite(cpu->bc,cpu->b);goto fast_1191; // OUT (C),B (1)
fast_1191:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();cpu->wz=cpu->bc+1;goto fast_1192; // OUT (C),B (2)
fast_1192:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1193; // OUT (C),B (3)
fast_1193:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1193; // OUT (C),B (4)
finish_1193:
    board_finish_slice(b,pins,elapsed,1193); return elapsed;
fast_1194:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1195; // SBC HL,BC (1)
fast_1195:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1196; // SBC HL,BC (2)
fast_1196:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1197; // SBC HL,BC (3)
fast_1197:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1198; // SBC HL,BC (4)
fast_1198:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1199; // SBC HL,BC (5)
fast_1199:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1200; // SBC HL,BC (6)
fast_1200:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1200; // SBC HL,BC (7)
finish_1200:
    board_finish_slice(b,pins,elapsed,1200); return elapsed;
fast_1201:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1202; // LD (nn),BC (1)
fast_1202:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_1203; // LD (nn),BC (2)
fast_1203:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1204; // LD (nn),BC (3)
fast_1204:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1205; // LD (nn),BC (4)
fast_1205:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();goto fast_1206; // LD (nn),BC (5)
fast_1206:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1207; // LD (nn),BC (6)
fast_1207:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->wz++,cpu->c);goto fast_1208; // LD (nn),BC (7)
fast_1208:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1209; // LD (nn),BC (8)
fast_1209:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1210; // LD (nn),BC (9)
fast_1210:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->wz,cpu->b);goto fast_1211; // LD (nn),BC (10)
fast_1211:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1212; // LD (nn),BC (11)
fast_1212:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1212; // LD (nn),BC (12)
finish_1212:
    board_finish_slice(b,pins,elapsed,1212); return elapsed;
fast_1213:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->sp++);goto fast_1214; // RETN (1)
fast_1214:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_1215; // RETN (2)
fast_1215:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1216; // RETN (3)
fast_1216:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->sp++);goto fast_1217; // RETN (4)
fast_1217:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();cpu->pc=cpu->wz;goto fast_1218; // RETN (5)
fast_1218:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins);cpu->iff1=cpu->iff2;goto finish_1218; // RETN (6)
finish_1218:
    board_finish_slice(b,pins,elapsed,1218); return elapsed;
fast_1219:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->i=cpu->a;pins=_z80_fetch(cpu,pins); goto finish_1219; // LD I,A (1)
finish_1219:
    board_finish_slice(b,pins,elapsed,1219); return elapsed;
fast_1220:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1221; // IN C,(C) (1)
fast_1221:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_ioread(cpu->bc);goto fast_1222; // IN C,(C) (2)
fast_1222:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();cpu->wz=cpu->bc+1;goto fast_1223; // IN C,(C) (3)
fast_1223:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->c=_z80_in(cpu,cpu->dlatch);pins=_z80_fetch(cpu,pins); goto finish_1223; // IN C,(C) (4)
finish_1223:
    board_finish_slice(b,pins,elapsed,1223); return elapsed;
fast_1224:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _iowrite(cpu->bc,cpu->c);goto fast_1225; // OUT (C),C (1)
fast_1225:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();cpu->wz=cpu->bc+1;goto fast_1226; // OUT (C),C (2)
fast_1226:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1227; // OUT (C),C (3)
fast_1227:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1227; // OUT (C),C (4)
finish_1227:
    board_finish_slice(b,pins,elapsed,1227); return elapsed;
fast_1228:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1229; // ADC HL,BC (1)
fast_1229:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1230; // ADC HL,BC (2)
fast_1230:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1231; // ADC HL,BC (3)
fast_1231:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1232; // ADC HL,BC (4)
fast_1232:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1233; // ADC HL,BC (5)
fast_1233:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1234; // ADC HL,BC (6)
fast_1234:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1234; // ADC HL,BC (7)
finish_1234:
    board_finish_slice(b,pins,elapsed,1234); return elapsed;
fast_1235:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1236; // LD BC,(nn) (1)
fast_1236:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_1237; // LD BC,(nn) (2)
fast_1237:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1238; // LD BC,(nn) (3)
fast_1238:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1239; // LD BC,(nn) (4)
fast_1239:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();goto fast_1240; // LD BC,(nn) (5)
fast_1240:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1241; // LD BC,(nn) (6)
fast_1241:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->wz++);goto fast_1242; // LD BC,(nn) (7)
fast_1242:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->c=_gd();goto fast_1243; // LD BC,(nn) (8)
fast_1243:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1244; // LD BC,(nn) (9)
fast_1244:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->wz);goto fast_1245; // LD BC,(nn) (10)
fast_1245:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->b=_gd();goto fast_1246; // LD BC,(nn) (11)
fast_1246:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1246; // LD BC,(nn) (12)
finish_1246:
    board_finish_slice(b,pins,elapsed,1246); return elapsed;
fast_1247:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->sp++);goto fast_1248; // RETI (1)
fast_1248:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();pins|=Z80_RETI;goto fast_1249; // RETI (2)
fast_1249:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1250; // RETI (3)
fast_1250:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->sp++);goto fast_1251; // RETI (4)
fast_1251:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();cpu->pc=cpu->wz;goto fast_1252; // RETI (5)
fast_1252:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins);cpu->iff1=cpu->iff2;goto finish_1252; // RETI (6)
finish_1252:
    board_finish_slice(b,pins,elapsed,1252); return elapsed;
fast_1253:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->r=cpu->a;pins=_z80_fetch(cpu,pins); goto finish_1253; // LD R,A (1)
finish_1253:
    board_finish_slice(b,pins,elapsed,1253); return elapsed;
fast_1254:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1255; // IN D,(C) (1)
fast_1255:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_ioread(cpu->bc);goto fast_1256; // IN D,(C) (2)
fast_1256:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();cpu->wz=cpu->bc+1;goto fast_1257; // IN D,(C) (3)
fast_1257:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->d=_z80_in(cpu,cpu->dlatch);pins=_z80_fetch(cpu,pins); goto finish_1257; // IN D,(C) (4)
finish_1257:
    board_finish_slice(b,pins,elapsed,1257); return elapsed;
fast_1258:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _iowrite(cpu->bc,cpu->d);goto fast_1259; // OUT (C),D (1)
fast_1259:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();cpu->wz=cpu->bc+1;goto fast_1260; // OUT (C),D (2)
fast_1260:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1261; // OUT (C),D (3)
fast_1261:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1261; // OUT (C),D (4)
finish_1261:
    board_finish_slice(b,pins,elapsed,1261); return elapsed;
fast_1262:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1263; // SBC HL,DE (1)
fast_1263:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1264; // SBC HL,DE (2)
fast_1264:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1265; // SBC HL,DE (3)
fast_1265:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1266; // SBC HL,DE (4)
fast_1266:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1267; // SBC HL,DE (5)
fast_1267:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1268; // SBC HL,DE (6)
fast_1268:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1268; // SBC HL,DE (7)
finish_1268:
    board_finish_slice(b,pins,elapsed,1268); return elapsed;
fast_1269:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1270; // LD (nn),DE (1)
fast_1270:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_1271; // LD (nn),DE (2)
fast_1271:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1272; // LD (nn),DE (3)
fast_1272:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1273; // LD (nn),DE (4)
fast_1273:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();goto fast_1274; // LD (nn),DE (5)
fast_1274:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1275; // LD (nn),DE (6)
fast_1275:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->wz++,cpu->e);goto fast_1276; // LD (nn),DE (7)
fast_1276:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1277; // LD (nn),DE (8)
fast_1277:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1278; // LD (nn),DE (9)
fast_1278:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->wz,cpu->d);goto fast_1279; // LD (nn),DE (10)
fast_1279:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1280; // LD (nn),DE (11)
fast_1280:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1280; // LD (nn),DE (12)
finish_1280:
    board_finish_slice(b,pins,elapsed,1280); return elapsed;
fast_1281:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins);cpu->iff1=cpu->iff2;goto finish_1281; // RETI (6)
finish_1281:
    board_finish_slice(b,pins,elapsed,1281); return elapsed;
fast_1282:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->a=cpu->i;cpu->f=_z80_sziff2_flags(cpu, cpu->i);pins=_z80_fetch(cpu,pins); goto finish_1282; // LD A,I (1)
finish_1282:
    board_finish_slice(b,pins,elapsed,1282); return elapsed;
fast_1283:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1284; // IN E,(C) (1)
fast_1284:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_ioread(cpu->bc);goto fast_1285; // IN E,(C) (2)
fast_1285:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();cpu->wz=cpu->bc+1;goto fast_1286; // IN E,(C) (3)
fast_1286:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->e=_z80_in(cpu,cpu->dlatch);pins=_z80_fetch(cpu,pins); goto finish_1286; // IN E,(C) (4)
finish_1286:
    board_finish_slice(b,pins,elapsed,1286); return elapsed;
fast_1287:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _iowrite(cpu->bc,cpu->e);goto fast_1288; // OUT (C),E (1)
fast_1288:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();cpu->wz=cpu->bc+1;goto fast_1289; // OUT (C),E (2)
fast_1289:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1290; // OUT (C),E (3)
fast_1290:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1290; // OUT (C),E (4)
finish_1290:
    board_finish_slice(b,pins,elapsed,1290); return elapsed;
fast_1291:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1292; // ADC HL,DE (1)
fast_1292:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1293; // ADC HL,DE (2)
fast_1293:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1294; // ADC HL,DE (3)
fast_1294:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1295; // ADC HL,DE (4)
fast_1295:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1296; // ADC HL,DE (5)
fast_1296:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1297; // ADC HL,DE (6)
fast_1297:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1297; // ADC HL,DE (7)
finish_1297:
    board_finish_slice(b,pins,elapsed,1297); return elapsed;
fast_1298:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1299; // LD DE,(nn) (1)
fast_1299:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_1300; // LD DE,(nn) (2)
fast_1300:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1301; // LD DE,(nn) (3)
fast_1301:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1302; // LD DE,(nn) (4)
fast_1302:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();goto fast_1303; // LD DE,(nn) (5)
fast_1303:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1304; // LD DE,(nn) (6)
fast_1304:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->wz++);goto fast_1305; // LD DE,(nn) (7)
fast_1305:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->e=_gd();goto fast_1306; // LD DE,(nn) (8)
fast_1306:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1307; // LD DE,(nn) (9)
fast_1307:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->wz);goto fast_1308; // LD DE,(nn) (10)
fast_1308:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->d=_gd();goto fast_1309; // LD DE,(nn) (11)
fast_1309:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1309; // LD DE,(nn) (12)
finish_1309:
    board_finish_slice(b,pins,elapsed,1309); return elapsed;
fast_1310:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins);cpu->iff1=cpu->iff2;goto finish_1310; // RETI (6)
finish_1310:
    board_finish_slice(b,pins,elapsed,1310); return elapsed;
fast_1311:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->a=cpu->r;cpu->f=_z80_sziff2_flags(cpu, cpu->r);pins=_z80_fetch(cpu,pins); goto finish_1311; // LD A,R (1)
finish_1311:
    board_finish_slice(b,pins,elapsed,1311); return elapsed;
fast_1312:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1313; // IN H,(C) (1)
fast_1313:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_ioread(cpu->bc);goto fast_1314; // IN H,(C) (2)
fast_1314:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();cpu->wz=cpu->bc+1;goto fast_1315; // IN H,(C) (3)
fast_1315:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->h=_z80_in(cpu,cpu->dlatch);pins=_z80_fetch(cpu,pins); goto finish_1315; // IN H,(C) (4)
finish_1315:
    board_finish_slice(b,pins,elapsed,1315); return elapsed;
fast_1316:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _iowrite(cpu->bc,cpu->h);goto fast_1317; // OUT (C),H (1)
fast_1317:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();cpu->wz=cpu->bc+1;goto fast_1318; // OUT (C),H (2)
fast_1318:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1319; // OUT (C),H (3)
fast_1319:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1319; // OUT (C),H (4)
finish_1319:
    board_finish_slice(b,pins,elapsed,1319); return elapsed;
fast_1320:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1321; // SBC HL,HL (1)
fast_1321:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1322; // SBC HL,HL (2)
fast_1322:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1323; // SBC HL,HL (3)
fast_1323:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1324; // SBC HL,HL (4)
fast_1324:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1325; // SBC HL,HL (5)
fast_1325:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1326; // SBC HL,HL (6)
fast_1326:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1326; // SBC HL,HL (7)
finish_1326:
    board_finish_slice(b,pins,elapsed,1326); return elapsed;
fast_1327:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1328; // LD (nn),HL (1)
fast_1328:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_1329; // LD (nn),HL (2)
fast_1329:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1330; // LD (nn),HL (3)
fast_1330:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1331; // LD (nn),HL (4)
fast_1331:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();goto fast_1332; // LD (nn),HL (5)
fast_1332:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1333; // LD (nn),HL (6)
fast_1333:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->wz++,cpu->l);goto fast_1334; // LD (nn),HL (7)
fast_1334:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1335; // LD (nn),HL (8)
fast_1335:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1336; // LD (nn),HL (9)
fast_1336:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->wz,cpu->h);goto fast_1337; // LD (nn),HL (10)
fast_1337:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1338; // LD (nn),HL (11)
fast_1338:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1338; // LD (nn),HL (12)
finish_1338:
    board_finish_slice(b,pins,elapsed,1338); return elapsed;
fast_1339:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins);cpu->iff1=cpu->iff2;goto finish_1339; // RETI (6)
finish_1339:
    board_finish_slice(b,pins,elapsed,1339); return elapsed;
fast_1340:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->hl);goto fast_1341; // RRD (1)
fast_1341:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();goto fast_1342; // RRD (2)
fast_1342:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_z80_rrd(cpu,cpu->dlatch);goto fast_1343; // RRD (3)
fast_1343:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1344; // RRD (4)
fast_1344:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1345; // RRD (5)
fast_1345:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1346; // RRD (6)
fast_1346:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1347; // RRD (7)
fast_1347:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->hl,cpu->dlatch);cpu->wz=cpu->hl+1;goto fast_1348; // RRD (8)
fast_1348:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1349; // RRD (9)
fast_1349:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1349; // RRD (10)
finish_1349:
    board_finish_slice(b,pins,elapsed,1349); return elapsed;
fast_1350:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1351; // IN L,(C) (1)
fast_1351:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_ioread(cpu->bc);goto fast_1352; // IN L,(C) (2)
fast_1352:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();cpu->wz=cpu->bc+1;goto fast_1353; // IN L,(C) (3)
fast_1353:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->l=_z80_in(cpu,cpu->dlatch);pins=_z80_fetch(cpu,pins); goto finish_1353; // IN L,(C) (4)
finish_1353:
    board_finish_slice(b,pins,elapsed,1353); return elapsed;
fast_1354:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _iowrite(cpu->bc,cpu->l);goto fast_1355; // OUT (C),L (1)
fast_1355:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();cpu->wz=cpu->bc+1;goto fast_1356; // OUT (C),L (2)
fast_1356:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1357; // OUT (C),L (3)
fast_1357:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1357; // OUT (C),L (4)
finish_1357:
    board_finish_slice(b,pins,elapsed,1357); return elapsed;
fast_1358:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1359; // ADC HL,HL (1)
fast_1359:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1360; // ADC HL,HL (2)
fast_1360:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1361; // ADC HL,HL (3)
fast_1361:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1362; // ADC HL,HL (4)
fast_1362:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1363; // ADC HL,HL (5)
fast_1363:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1364; // ADC HL,HL (6)
fast_1364:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1364; // ADC HL,HL (7)
finish_1364:
    board_finish_slice(b,pins,elapsed,1364); return elapsed;
fast_1365:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1366; // LD HL,(nn) (1)
fast_1366:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_1367; // LD HL,(nn) (2)
fast_1367:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1368; // LD HL,(nn) (3)
fast_1368:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1369; // LD HL,(nn) (4)
fast_1369:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();goto fast_1370; // LD HL,(nn) (5)
fast_1370:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1371; // LD HL,(nn) (6)
fast_1371:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->wz++);goto fast_1372; // LD HL,(nn) (7)
fast_1372:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->l=_gd();goto fast_1373; // LD HL,(nn) (8)
fast_1373:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1374; // LD HL,(nn) (9)
fast_1374:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->wz);goto fast_1375; // LD HL,(nn) (10)
fast_1375:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->h=_gd();goto fast_1376; // LD HL,(nn) (11)
fast_1376:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1376; // LD HL,(nn) (12)
finish_1376:
    board_finish_slice(b,pins,elapsed,1376); return elapsed;
fast_1377:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins);cpu->iff1=cpu->iff2;goto finish_1377; // RETI (6)
finish_1377:
    board_finish_slice(b,pins,elapsed,1377); return elapsed;
fast_1378:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->hl);goto fast_1379; // RLD (1)
fast_1379:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();goto fast_1380; // RLD (2)
fast_1380:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_z80_rld(cpu,cpu->dlatch);goto fast_1381; // RLD (3)
fast_1381:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1382; // RLD (4)
fast_1382:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1383; // RLD (5)
fast_1383:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1384; // RLD (6)
fast_1384:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1385; // RLD (7)
fast_1385:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->hl,cpu->dlatch);cpu->wz=cpu->hl+1;goto fast_1386; // RLD (8)
fast_1386:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1387; // RLD (9)
fast_1387:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1387; // RLD (10)
finish_1387:
    board_finish_slice(b,pins,elapsed,1387); return elapsed;
fast_1388:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1389; // IN (C) (1)
fast_1389:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_ioread(cpu->bc);goto fast_1390; // IN (C) (2)
fast_1390:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();cpu->wz=cpu->bc+1;goto fast_1391; // IN (C) (3)
fast_1391:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_in(cpu,cpu->dlatch);pins=_z80_fetch(cpu,pins); goto finish_1391; // IN (C) (4)
finish_1391:
    board_finish_slice(b,pins,elapsed,1391); return elapsed;
fast_1392:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _iowrite(cpu->bc,b->model ? 255 : 0);goto fast_1393; // OUT (C),0 (1)
fast_1393:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();cpu->wz=cpu->bc+1;goto fast_1394; // OUT (C),0 (2)
fast_1394:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1395; // OUT (C),0 (3)
fast_1395:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1395; // OUT (C),0 (4)
finish_1395:
    board_finish_slice(b,pins,elapsed,1395); return elapsed;
fast_1396:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1397; // SBC HL,SP (1)
fast_1397:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1398; // SBC HL,SP (2)
fast_1398:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1399; // SBC HL,SP (3)
fast_1399:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1400; // SBC HL,SP (4)
fast_1400:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1401; // SBC HL,SP (5)
fast_1401:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1402; // SBC HL,SP (6)
fast_1402:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1402; // SBC HL,SP (7)
finish_1402:
    board_finish_slice(b,pins,elapsed,1402); return elapsed;
fast_1403:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1404; // LD (nn),SP (1)
fast_1404:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_1405; // LD (nn),SP (2)
fast_1405:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1406; // LD (nn),SP (3)
fast_1406:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1407; // LD (nn),SP (4)
fast_1407:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();goto fast_1408; // LD (nn),SP (5)
fast_1408:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1409; // LD (nn),SP (6)
fast_1409:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->wz++,cpu->spl);goto fast_1410; // LD (nn),SP (7)
fast_1410:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1411; // LD (nn),SP (8)
fast_1411:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1412; // LD (nn),SP (9)
fast_1412:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->wz,cpu->sph);goto fast_1413; // LD (nn),SP (10)
fast_1413:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1414; // LD (nn),SP (11)
fast_1414:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1414; // LD (nn),SP (12)
finish_1414:
    board_finish_slice(b,pins,elapsed,1414); return elapsed;
fast_1415:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins);cpu->iff1=cpu->iff2;goto finish_1415; // RETI (6)
finish_1415:
    board_finish_slice(b,pins,elapsed,1415); return elapsed;
fast_1416:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1417; // IN A,(C) (1)
fast_1417:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_ioread(cpu->bc);goto fast_1418; // IN A,(C) (2)
fast_1418:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();cpu->wz=cpu->bc+1;goto fast_1419; // IN A,(C) (3)
fast_1419:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->a=_z80_in(cpu,cpu->dlatch);pins=_z80_fetch(cpu,pins); goto finish_1419; // IN A,(C) (4)
finish_1419:
    board_finish_slice(b,pins,elapsed,1419); return elapsed;
fast_1420:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _iowrite(cpu->bc,cpu->a);goto fast_1421; // OUT (C),A (1)
fast_1421:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();cpu->wz=cpu->bc+1;goto fast_1422; // OUT (C),A (2)
fast_1422:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1423; // OUT (C),A (3)
fast_1423:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1423; // OUT (C),A (4)
finish_1423:
    board_finish_slice(b,pins,elapsed,1423); return elapsed;
fast_1424:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1425; // ADC HL,SP (1)
fast_1425:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1426; // ADC HL,SP (2)
fast_1426:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1427; // ADC HL,SP (3)
fast_1427:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1428; // ADC HL,SP (4)
fast_1428:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1429; // ADC HL,SP (5)
fast_1429:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1430; // ADC HL,SP (6)
fast_1430:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1430; // ADC HL,SP (7)
finish_1430:
    board_finish_slice(b,pins,elapsed,1430); return elapsed;
fast_1431:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1432; // LD SP,(nn) (1)
fast_1432:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzl=_gd();goto fast_1433; // LD SP,(nn) (2)
fast_1433:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1434; // LD SP,(nn) (3)
fast_1434:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1435; // LD SP,(nn) (4)
fast_1435:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();goto fast_1436; // LD SP,(nn) (5)
fast_1436:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1437; // LD SP,(nn) (6)
fast_1437:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->wz++);goto fast_1438; // LD SP,(nn) (7)
fast_1438:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->spl=_gd();goto fast_1439; // LD SP,(nn) (8)
fast_1439:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1440; // LD SP,(nn) (9)
fast_1440:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->wz);goto fast_1441; // LD SP,(nn) (10)
fast_1441:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->sph=_gd();goto fast_1442; // LD SP,(nn) (11)
fast_1442:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1442; // LD SP,(nn) (12)
finish_1442:
    board_finish_slice(b,pins,elapsed,1442); return elapsed;
fast_1443:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins);cpu->iff1=cpu->iff2;goto finish_1443; // RETI (6)
finish_1443:
    board_finish_slice(b,pins,elapsed,1443); return elapsed;
fast_1444:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->hl++);goto fast_1445; // LDI (1)
fast_1445:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();goto fast_1446; // LDI (2)
fast_1446:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1447; // LDI (3)
fast_1447:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->de++,cpu->dlatch);goto fast_1448; // LDI (4)
fast_1448:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1449; // LDI (5)
fast_1449:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_ldi_ldd(cpu,cpu->dlatch);goto fast_1450; // LDI (6)
fast_1450:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1451; // LDI (7)
fast_1451:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1451; // LDI (8)
finish_1451:
    board_finish_slice(b,pins,elapsed,1451); return elapsed;
fast_1452:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->hl++);goto fast_1453; // CPI (1)
fast_1453:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();goto fast_1454; // CPI (2)
fast_1454:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wz++;_z80_cpi_cpd(cpu,cpu->dlatch);goto fast_1455; // CPI (3)
fast_1455:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1456; // CPI (4)
fast_1456:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1457; // CPI (5)
fast_1457:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1458; // CPI (6)
fast_1458:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1459; // CPI (7)
fast_1459:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1459; // CPI (8)
finish_1459:
    board_finish_slice(b,pins,elapsed,1459); return elapsed;
fast_1460:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1461; // INI (1)
fast_1461:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1462; // INI (2)
fast_1462:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_ioread(cpu->bc);goto fast_1463; // INI (3)
fast_1463:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();cpu->wz=cpu->bc+1;cpu->b--;;goto fast_1464; // INI (4)
fast_1464:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1465; // INI (5)
fast_1465:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->hl++,cpu->dlatch);_z80_ini_ind(cpu,cpu->dlatch,cpu->c+1);goto fast_1466; // INI (6)
fast_1466:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1467; // INI (7)
fast_1467:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1467; // INI (8)
finish_1467:
    board_finish_slice(b,pins,elapsed,1467); return elapsed;
fast_1468:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1469; // OUTI (1)
fast_1469:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->hl++);goto fast_1470; // OUTI (2)
fast_1470:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();cpu->b--;goto fast_1471; // OUTI (3)
fast_1471:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1472; // OUTI (4)
fast_1472:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _iowrite(cpu->bc,cpu->dlatch);goto fast_1473; // OUTI (5)
fast_1473:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();cpu->wz=cpu->bc+1;_z80_outi_outd(cpu,cpu->dlatch);goto fast_1474; // OUTI (6)
fast_1474:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1475; // OUTI (7)
fast_1475:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1475; // OUTI (8)
finish_1475:
    board_finish_slice(b,pins,elapsed,1475); return elapsed;
fast_1476:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->hl--);goto fast_1477; // LDD (1)
fast_1477:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();goto fast_1478; // LDD (2)
fast_1478:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1479; // LDD (3)
fast_1479:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->de--,cpu->dlatch);goto fast_1480; // LDD (4)
fast_1480:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1481; // LDD (5)
fast_1481:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_ldi_ldd(cpu,cpu->dlatch);goto fast_1482; // LDD (6)
fast_1482:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1483; // LDD (7)
fast_1483:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1483; // LDD (8)
finish_1483:
    board_finish_slice(b,pins,elapsed,1483); return elapsed;
fast_1484:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->hl--);goto fast_1485; // CPD (1)
fast_1485:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();goto fast_1486; // CPD (2)
fast_1486:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wz--;_z80_cpi_cpd(cpu,cpu->dlatch);goto fast_1487; // CPD (3)
fast_1487:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1488; // CPD (4)
fast_1488:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1489; // CPD (5)
fast_1489:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1490; // CPD (6)
fast_1490:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1491; // CPD (7)
fast_1491:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1491; // CPD (8)
finish_1491:
    board_finish_slice(b,pins,elapsed,1491); return elapsed;
fast_1492:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1493; // IND (1)
fast_1493:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1494; // IND (2)
fast_1494:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_ioread(cpu->bc);goto fast_1495; // IND (3)
fast_1495:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();cpu->wz=cpu->bc-1;cpu->b--;;goto fast_1496; // IND (4)
fast_1496:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1497; // IND (5)
fast_1497:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->hl--,cpu->dlatch);_z80_ini_ind(cpu,cpu->dlatch,cpu->c-1);goto fast_1498; // IND (6)
fast_1498:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1499; // IND (7)
fast_1499:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1499; // IND (8)
finish_1499:
    board_finish_slice(b,pins,elapsed,1499); return elapsed;
fast_1500:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1501; // OUTD (1)
fast_1501:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->hl--);goto fast_1502; // OUTD (2)
fast_1502:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();cpu->b--;goto fast_1503; // OUTD (3)
fast_1503:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1504; // OUTD (4)
fast_1504:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _iowrite(cpu->bc,cpu->dlatch);goto fast_1505; // OUTD (5)
fast_1505:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();cpu->wz=cpu->bc-1;_z80_outi_outd(cpu,cpu->dlatch);goto fast_1506; // OUTD (6)
fast_1506:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1507; // OUTD (7)
fast_1507:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1507; // OUTD (8)
finish_1507:
    board_finish_slice(b,pins,elapsed,1507); return elapsed;
fast_1508:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->hl++);goto fast_1509; // LDIR (1)
fast_1509:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();goto fast_1510; // LDIR (2)
fast_1510:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1511; // LDIR (3)
fast_1511:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->de++,cpu->dlatch);goto fast_1512; // LDIR (4)
fast_1512:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1513; // LDIR (5)
fast_1513:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    if(!_z80_ldi_ldd(cpu,cpu->dlatch)){goto fast_1519;};goto fast_1514; // LDIR (6)
fast_1514:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1515; // LDIR (7)
fast_1515:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wz=--cpu->pc;--cpu->pc;board_repeat_flags(cpu,false);;goto fast_1516; // LDIR (8)
fast_1516:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1517; // LDIR (9)
fast_1517:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1518; // LDIR (10)
fast_1518:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1519; // LDIR (11)
fast_1519:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1520; // LDIR (12)
fast_1520:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1520; // LDIR (13)
finish_1520:
    board_finish_slice(b,pins,elapsed,1520); return elapsed;
fast_1521:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->hl++);goto fast_1522; // CPIR (1)
fast_1522:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();goto fast_1523; // CPIR (2)
fast_1523:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wz++;if(!_z80_cpi_cpd(cpu,cpu->dlatch)){goto fast_1529;};goto fast_1524; // CPIR (3)
fast_1524:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1525; // CPIR (4)
fast_1525:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1526; // CPIR (5)
fast_1526:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1527; // CPIR (6)
fast_1527:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1528; // CPIR (7)
fast_1528:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wz=--cpu->pc;--cpu->pc;board_repeat_flags(cpu,false);goto fast_1529; // CPIR (8)
fast_1529:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1530; // CPIR (9)
fast_1530:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1531; // CPIR (10)
fast_1531:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1532; // CPIR (11)
fast_1532:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1533; // CPIR (12)
fast_1533:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1533; // CPIR (13)
finish_1533:
    board_finish_slice(b,pins,elapsed,1533); return elapsed;
fast_1534:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1535; // INIR (1)
fast_1535:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1536; // INIR (2)
fast_1536:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_ioread(cpu->bc);goto fast_1537; // INIR (3)
fast_1537:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();cpu->wz=cpu->bc+1;cpu->b--;;goto fast_1538; // INIR (4)
fast_1538:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1539; // INIR (5)
fast_1539:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->hl++,cpu->dlatch);if (!_z80_ini_ind(cpu,cpu->dlatch,cpu->c+1)){goto fast_1545;};goto fast_1540; // INIR (6)
fast_1540:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1541; // INIR (7)
fast_1541:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wz=--cpu->pc;--cpu->pc;board_repeat_flags(cpu,true);goto fast_1542; // INIR (8)
fast_1542:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1543; // INIR (9)
fast_1543:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1544; // INIR (10)
fast_1544:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1545; // INIR (11)
fast_1545:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1546; // INIR (12)
fast_1546:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1546; // INIR (13)
finish_1546:
    board_finish_slice(b,pins,elapsed,1546); return elapsed;
fast_1547:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1548; // OTIR (1)
fast_1548:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->hl++);goto fast_1549; // OTIR (2)
fast_1549:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();cpu->b--;goto fast_1550; // OTIR (3)
fast_1550:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1551; // OTIR (4)
fast_1551:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _iowrite(cpu->bc,cpu->dlatch);goto fast_1552; // OTIR (5)
fast_1552:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();cpu->wz=cpu->bc+1;if(!_z80_outi_outd(cpu,cpu->dlatch)){goto fast_1558;};goto fast_1553; // OTIR (6)
fast_1553:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1554; // OTIR (7)
fast_1554:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wz=--cpu->pc;--cpu->pc;board_repeat_flags(cpu,true);goto fast_1555; // OTIR (8)
fast_1555:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1556; // OTIR (9)
fast_1556:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1557; // OTIR (10)
fast_1557:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1558; // OTIR (11)
fast_1558:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1559; // OTIR (12)
fast_1559:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1559; // OTIR (13)
finish_1559:
    board_finish_slice(b,pins,elapsed,1559); return elapsed;
fast_1560:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->hl--);goto fast_1561; // LDDR (1)
fast_1561:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();goto fast_1562; // LDDR (2)
fast_1562:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1563; // LDDR (3)
fast_1563:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->de--,cpu->dlatch);goto fast_1564; // LDDR (4)
fast_1564:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1565; // LDDR (5)
fast_1565:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    if(!_z80_ldi_ldd(cpu,cpu->dlatch)){goto fast_1571;};goto fast_1566; // LDDR (6)
fast_1566:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1567; // LDDR (7)
fast_1567:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wz=--cpu->pc;--cpu->pc;board_repeat_flags(cpu,false);;goto fast_1568; // LDDR (8)
fast_1568:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1569; // LDDR (9)
fast_1569:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1570; // LDDR (10)
fast_1570:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1571; // LDDR (11)
fast_1571:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1572; // LDDR (12)
fast_1572:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1572; // LDDR (13)
finish_1572:
    board_finish_slice(b,pins,elapsed,1572); return elapsed;
fast_1573:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->hl--);goto fast_1574; // CPDR (1)
fast_1574:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();goto fast_1575; // CPDR (2)
fast_1575:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wz--;if(!_z80_cpi_cpd(cpu,cpu->dlatch)){goto fast_1581;};goto fast_1576; // CPDR (3)
fast_1576:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1577; // CPDR (4)
fast_1577:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1578; // CPDR (5)
fast_1578:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1579; // CPDR (6)
fast_1579:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1580; // CPDR (7)
fast_1580:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wz=--cpu->pc;--cpu->pc;board_repeat_flags(cpu,false);goto fast_1581; // CPDR (8)
fast_1581:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1582; // CPDR (9)
fast_1582:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1583; // CPDR (10)
fast_1583:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1584; // CPDR (11)
fast_1584:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1585; // CPDR (12)
fast_1585:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1585; // CPDR (13)
finish_1585:
    board_finish_slice(b,pins,elapsed,1585); return elapsed;
fast_1586:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1587; // INDR (1)
fast_1587:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1588; // INDR (2)
fast_1588:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_ioread(cpu->bc);goto fast_1589; // INDR (3)
fast_1589:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();cpu->wz=cpu->bc-1;cpu->b--;;goto fast_1590; // INDR (4)
fast_1590:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1591; // INDR (5)
fast_1591:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->hl--,cpu->dlatch);if (!_z80_ini_ind(cpu,cpu->dlatch,cpu->c-1)){goto fast_1597;};goto fast_1592; // INDR (6)
fast_1592:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1593; // INDR (7)
fast_1593:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wz=--cpu->pc;--cpu->pc;board_repeat_flags(cpu,true);goto fast_1594; // INDR (8)
fast_1594:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1595; // INDR (9)
fast_1595:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1596; // INDR (10)
fast_1596:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1597; // INDR (11)
fast_1597:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1598; // INDR (12)
fast_1598:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1598; // INDR (13)
finish_1598:
    board_finish_slice(b,pins,elapsed,1598); return elapsed;
fast_1599:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1600; // OTDR (1)
fast_1600:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->hl--);goto fast_1601; // OTDR (2)
fast_1601:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();cpu->b--;goto fast_1602; // OTDR (3)
fast_1602:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1603; // OTDR (4)
fast_1603:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _iowrite(cpu->bc,cpu->dlatch);goto fast_1604; // OTDR (5)
fast_1604:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();cpu->wz=cpu->bc-1;if(!_z80_outi_outd(cpu,cpu->dlatch)){goto fast_1610;};goto fast_1605; // OTDR (6)
fast_1605:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1606; // OTDR (7)
fast_1606:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wz=--cpu->pc;--cpu->pc;board_repeat_flags(cpu,true);goto fast_1607; // OTDR (8)
fast_1607:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1608; // OTDR (9)
fast_1608:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1609; // OTDR (10)
fast_1609:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1610; // OTDR (11)
fast_1610:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1611; // OTDR (12)
fast_1611:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1611; // OTDR (13)
finish_1611:
    board_finish_slice(b,pins,elapsed,1611); return elapsed;
fast_1612:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    {uint8_t z=cpu->opcode&7;_z80_cb_action(cpu,z,z);};pins=_z80_fetch(cpu,pins); goto finish_1612; // cb (0)
finish_1612:
    board_finish_slice(b,pins,elapsed,1612); return elapsed;
fast_1613:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1614; // cbhl (0)
fast_1614:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->hl);goto fast_1615; // cbhl (1)
fast_1615:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();if(!_z80_cb_action(cpu,6,6)){goto fast_1619;};goto fast_1616; // cbhl (2)
fast_1616:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1617; // cbhl (3)
fast_1617:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1618; // cbhl (4)
fast_1618:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->hl,cpu->dlatch);goto fast_1619; // cbhl (5)
fast_1619:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1620; // cbhl (6)
fast_1620:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1620; // cbhl (7)
finish_1620:
    board_finish_slice(b,pins,elapsed,1620); return elapsed;
fast_1621:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1622; // ddfdcb (0)
fast_1622:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _z80_ddfdcb_addr(cpu,pins);goto fast_1623; // ddfdcb (1)
fast_1623:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1624; // ddfdcb (2)
fast_1624:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->pc++);goto fast_1625; // ddfdcb (3)
fast_1625:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->opcode=_gd();goto fast_1626; // ddfdcb (4)
fast_1626:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1627; // ddfdcb (5)
fast_1627:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1628; // ddfdcb (6)
fast_1628:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1629; // ddfdcb (7)
fast_1629:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->addr);goto fast_1630; // ddfdcb (8)
fast_1630:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();if(!_z80_cb_action(cpu,6,cpu->opcode&7)){goto fast_1634;};goto fast_1631; // ddfdcb (9)
fast_1631:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1632; // ddfdcb (10)
fast_1632:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1633; // ddfdcb (11)
fast_1633:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(cpu->addr,cpu->dlatch);goto fast_1634; // ddfdcb (12)
fast_1634:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1635; // ddfdcb (13)
fast_1635:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1635; // ddfdcb (14)
finish_1635:
    board_finish_slice(b,pins,elapsed,1635); return elapsed;
fast_1636:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->iff1=cpu->iff2=false;goto fast_1637; // int_im0 (0)
fast_1637:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins|=(Z80_M1|Z80_IORQ);goto fast_1638; // int_im0 (1)
fast_1638:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();cpu->opcode=_z80_get_db(pins);goto fast_1639; // int_im0 (2)
fast_1639:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_refresh(cpu,pins);goto fast_1640; // int_im0 (3)
fast_1640:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->addr=cpu->hl;{ cpu->step=cpu->opcode; goto fast_dispatch; };goto fast_1641; // int_im0 (4)
fast_1641:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1641; // int_im0 (5)
finish_1641:
    board_finish_slice(b,pins,elapsed,1641); return elapsed;
fast_1642:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->iff1=cpu->iff2=false;goto fast_1643; // int_im1 (0)
fast_1643:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins|=(Z80_M1|Z80_IORQ);goto fast_1644; // int_im1 (1)
fast_1644:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();goto fast_1645; // int_im1 (2)
fast_1645:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_refresh(cpu,pins);goto fast_1646; // int_im1 (3)
fast_1646:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1647; // int_im1 (4)
fast_1647:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1648; // int_im1 (5)
fast_1648:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1649; // int_im1 (6)
fast_1649:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pch);goto fast_1650; // int_im1 (7)
fast_1650:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1651; // int_im1 (8)
fast_1651:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1652; // int_im1 (9)
fast_1652:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pcl);cpu->wz=cpu->pc=0x0038;goto fast_1653; // int_im1 (10)
fast_1653:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1654; // int_im1 (11)
fast_1654:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1654; // int_im1 (12)
finish_1654:
    board_finish_slice(b,pins,elapsed,1654); return elapsed;
fast_1655:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->iff1=cpu->iff2=false;goto fast_1656; // int_im2 (0)
fast_1656:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins|=(Z80_M1|Z80_IORQ);goto fast_1657; // int_im2 (1)
fast_1657:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();cpu->dlatch=_z80_get_db(pins);goto fast_1658; // int_im2 (2)
fast_1658:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_refresh(cpu,pins);goto fast_1659; // int_im2 (3)
fast_1659:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1660; // int_im2 (4)
fast_1660:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1661; // int_im2 (5)
fast_1661:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1662; // int_im2 (6)
fast_1662:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pch);goto fast_1663; // int_im2 (7)
fast_1663:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1664; // int_im2 (8)
fast_1664:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1665; // int_im2 (9)
fast_1665:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pcl);cpu->wzl=cpu->dlatch;cpu->wzh=cpu->i;goto fast_1666; // int_im2 (10)
fast_1666:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1667; // int_im2 (11)
fast_1667:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1668; // int_im2 (12)
fast_1668:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->wz++);goto fast_1669; // int_im2 (13)
fast_1669:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->dlatch=_gd();goto fast_1670; // int_im2 (14)
fast_1670:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1671; // int_im2 (15)
fast_1671:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mread(cpu->wz);goto fast_1672; // int_im2 (16)
fast_1672:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->wzh=_gd();cpu->wzl=cpu->dlatch;cpu->pc=cpu->wz;goto fast_1673; // int_im2 (17)
fast_1673:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1673; // int_im2 (18)
finish_1673:
    board_finish_slice(b,pins,elapsed,1673); return elapsed;
fast_1674:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();cpu->iff1=false;goto fast_1675; // nmi (0)
fast_1675:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_refresh(cpu,pins);goto fast_1676; // nmi (1)
fast_1676:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1677; // nmi (2)
fast_1677:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1678; // nmi (3)
fast_1678:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1679; // nmi (4)
fast_1679:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pch);goto fast_1680; // nmi (5)
fast_1680:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1681; // nmi (6)
fast_1681:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1682; // nmi (7)
fast_1682:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait();_mwrite(--cpu->sp,cpu->pcl);cpu->wz=cpu->pc=0x0066;goto fast_1683; // nmi (8)
fast_1683:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_1684; // nmi (9)
fast_1684:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_1684; // nmi (10)
        // %>
        //=== shared fetch machine cycle for DD/FD-prefixed ops
finish_1684:
    board_finish_slice(b,pins,elapsed,1684); return elapsed;
fast_Z80_DDFD_M1_T2:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait(); cpu->opcode = _gd(); goto fast_Z80_DDFD_M1_T3;
fast_Z80_DDFD_M1_T3:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins = _z80_refresh(cpu, pins); goto fast_Z80_DDFD_M1_T4;
fast_Z80_DDFD_M1_T4:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->addr = cpu->hlx[cpu->hlx_idx].hl;
            { cpu->step=_z80_indirect_table[cpu->opcode] ? Z80_DDFD_D_T1 : cpu->opcode; goto fast_dispatch; };
        //=== optional d-loading cycle for (IX+d), (IY+d)
fast_Z80_DDFD_D_T1:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_Z80_DDFD_D_T2;
fast_Z80_DDFD_D_T2:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait(); _mread(cpu->pc++); goto fast_Z80_DDFD_D_T3;
fast_Z80_DDFD_D_T3:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->addr += (int8_t)_gd(); cpu->wz = cpu->addr; goto fast_Z80_DDFD_D_T4;
        //--- special case LD (IX/IY+d),n or filler ticks
fast_Z80_DDFD_D_T4:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_Z80_DDFD_D_T5;
fast_Z80_DDFD_D_T5:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    if (cpu->opcode == 0x36) { _wait();_mread(cpu->pc++); }; goto fast_Z80_DDFD_D_T6;
fast_Z80_DDFD_D_T6:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    if (cpu->opcode == 0x36) { cpu->dlatch = _gd(); }; goto fast_Z80_DDFD_D_T7;
fast_Z80_DDFD_D_T7:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_Z80_DDFD_D_T8;
fast_Z80_DDFD_D_T8:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    { cpu->step=(cpu->opcode==0x36) ? Z80_DDFD_LDHLN_WR_T1 : cpu->opcode; goto fast_dispatch; };
        //--- special case LD (IX/IY+d),n write mcycle
fast_Z80_DDFD_LDHLN_WR_T1:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_Z80_DDFD_LDHLN_WR_T2;
fast_Z80_DDFD_LDHLN_WR_T2:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait(); _mwrite(cpu->addr,cpu->dlatch); goto fast_Z80_DDFD_LDHLN_WR_T3;
fast_Z80_DDFD_LDHLN_WR_T3:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    goto fast_Z80_DDFD_LDHLN_OVERLAPPED;
fast_Z80_DDFD_LDHLN_OVERLAPPED:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins=_z80_fetch(cpu,pins); goto finish_Z80_DDFD_LDHLN_OVERLAPPED;
        //=== special opcode fetch machine cycle for CB-prefixed instructions
finish_Z80_DDFD_LDHLN_OVERLAPPED:
    board_finish_slice(b,pins,elapsed,Z80_DDFD_LDHLN_OVERLAPPED); return elapsed;
fast_Z80_CB_M1_T2:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait(); cpu->opcode = _gd(); goto fast_Z80_CB_M1_T3;
fast_Z80_CB_M1_T3:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins = _z80_refresh(cpu, pins); goto fast_Z80_CB_M1_T4;
fast_Z80_CB_M1_T4:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    if ((cpu->opcode & 7) == 6) {
                // this is a (HL) instruction
                cpu->addr = cpu->hl;
                goto fast_1613;
            }
            else {
                goto fast_1612;
            }
        //=== special opcode fetch machine cycle for ED-prefixed instructions
fast_Z80_ED_M1_T2:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait(); cpu->opcode = _gd(); goto fast_Z80_ED_M1_T3;
fast_Z80_ED_M1_T3:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins = _z80_refresh(cpu, pins); goto fast_Z80_ED_M1_T4;
fast_Z80_ED_M1_T4:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    { cpu->step=cpu->opcode + 256; goto fast_dispatch; };
        //=== shared fetch machine cycle for non-DD/FD-prefixed ops
fast_Z80_M1_T2:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    _wait(); cpu->opcode = _gd(); goto fast_Z80_M1_T3;
fast_Z80_M1_T3:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    pins = _z80_refresh(cpu, pins); goto fast_Z80_M1_T4;
fast_Z80_M1_T4:
    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);
    cpu->addr = cpu->hl; { cpu->step=cpu->opcode; goto fast_dispatch; };
}


#undef _sa
#undef _sax
#undef _sad
#undef _sadx
#undef _gd
#undef _goto
#undef _fetch
#undef _fetch_dd
#undef _fetch_fd
#undef _fetch_ed
#undef _fetch_cb
#undef _mread
#undef _mwrite
#undef _ioread
#undef _iowrite
#undef _wait
#undef _cc_nz
#undef _cc_z
#undef _cc_nc
#undef _cc_c
#undef _cc_po
#undef _cc_pe
#undef _cc_p
#undef _cc_m
