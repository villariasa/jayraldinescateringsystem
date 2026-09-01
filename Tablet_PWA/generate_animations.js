const fs = require("fs");
const path = require("path");

const OUT_DIR = path.join(__dirname, "frontend", "animations");
if (!fs.existsSync(OUT_DIR)) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
}

function makeColor(hex, alpha = 1) {
  hex = hex.replace("#", "");
  return [
    parseInt(hex.substring(0, 2), 16) / 255,
    parseInt(hex.substring(2, 4), 16) / 255,
    parseInt(hex.substring(4, 6), 16) / 255,
    alpha
  ];
}

function baseLottie(name, w = 120, h = 120, op = 120, fr = 60) {
  return {
    v: "5.7.4",
    fr,
    ip: 0,
    op,
    w,
    h,
    nm: name,
    ddd: 0,
    assets: [],
    layers: []
  };
}

function makeTr(p = [0, 0], a = [0, 0], s = [100, 100], r = 0, o = 100) {
  return {
    ty: "tr",
    p: { a: Array.isArray(p[0]) ? 1 : 0, k: p },
    a: { a: 0, k: a },
    s: { a: Array.isArray(s[0]) ? 1 : 0, k: s },
    r: { a: typeof r === "object" ? 1 : 0, k: r },
    o: { a: typeof o === "object" ? 1 : 0, k: o },
    sk: { a: 0, k: 0 },
    sa: { a: 0, k: 0 },
    nm: "Tr"
  };
}

// ── 1. LOGO SPLASH (Entrance, Floating Cloche, Steam Wisps, Shimmer) ──
function buildLogoSplash() {
  const logoPath = path.join(__dirname, "frontend", "icons", "logo.png");
  let logoB64 = "";
  try {
    logoB64 = fs.readFileSync(logoPath).toString("base64");
  } catch (_) {}

  const l = baseLottie("Jayraldine Official Logo Lottie", 260, 260, 150, 60);
  l.assets = [
    {
      id: "official_logo",
      w: 500,
      h: 500,
      u: "",
      p: "data:image/png;base64," + logoB64,
      e: 1
    }
  ];

  // Layer 1: Glow Ring Outer
  l.layers.push({
    ddd: 0, ind: 1, ty: 4, nm: "Outer Glow Halo", sr: 1,
    ks: {
      o: { a: 1, k: [
        { t: 0, s: [45], e: [85], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
        { t: 75, s: [85], e: [45], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
        { t: 150, s: [45] }
      ]},
      r: { a: 0, k: 0 },
      p: { a: 0, k: [130, 130, 0] },
      a: { a: 0, k: [0, 0, 0] },
      s: { a: 1, k: [
        { t: 0, s: [96, 96, 100], e: [106, 106, 100], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
        { t: 75, s: [106, 106, 100], e: [96, 96, 100], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
        { t: 150, s: [96, 96, 100] }
      ]}
    },
    ao: 0,
    shapes: [{
      ty: "gr",
      it: [
        { ty: "el", d: 1, p: { a: 0, k: [0, 0] }, s: { a: 0, k: [208, 208] }, nm: "Circle" },
        { ty: "st", c: { a: 0, k: makeColor("#F59E0B") }, o: { a: 0, k: 65 }, w: { a: 0, k: 5 }, lc: 2, lj: 2, nm: "Stroke" },
        makeTr()
      ],
      nm: "RingGroup"
    }],
    ip: 0, op: 150, st: 0, bm: 0
  });

  // Layer 2-5: Twinkling Orbiting Stars
  for (let i = 0; i < 4; i++) {
    const baseAngle = (i * 90);
    l.layers.push({
      ddd: 0, ind: 2 + i, ty: 4, nm: "Star " + (i + 1), sr: 1,
      ks: {
        o: { a: 1, k: [
          { t: i * 20, s: [20], e: [100], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: i * 20 + 35, s: [100], e: [20], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 150, s: [20] }
        ]},
        r: { a: 1, k: [
          { t: 0, s: [baseAngle], e: [baseAngle + 360], i: { x: [0.5], y: [1] }, o: { x: [0.5], y: [0] } },
          { t: 150, s: [baseAngle + 360] }
        ]},
        p: { a: 0, k: [130, 130, 0] },
        a: { a: 0, k: [0, 114, 0] },
        s: { a: 1, k: [
          { t: i * 20, s: [60, 60, 100], e: [115, 115, 100], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: i * 20 + 35, s: [115, 115, 100], e: [60, 60, 100], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 150, s: [60, 60, 100] }
        ]}
      },
      ao: 0,
      shapes: [{
        ty: "gr",
        it: [
          {
            ty: "sh", d: 1,
            ks: {
              a: 0,
              k: {
                c: true,
                v: [[0, -8], [2.5, -2.5], [8, 0], [2.5, 2.5], [0, 8], [-2.5, 2.5], [-8, 0], [-2.5, -2.5]],
                i: [[0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0]],
                o: [[0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0]]
              }
            },
            nm: "StarPath"
          },
          { ty: "fl", c: { a: 0, k: makeColor("#F59E0B") }, o: { a: 0, k: 95 }, nm: "StarFill" },
          makeTr()
        ],
        nm: "StarGroup"
      }],
      ip: 0, op: 150, st: 0, bm: 0
    });
  }

  // Layer 6-8: Steam Wisps
  for (let i = 0; i < 3; i++) {
    const xOff = (i - 1) * 26;
    l.layers.push({
      ddd: 0, ind: 7 + i, ty: 4, nm: "Steam Wisp " + i, sr: 1,
      ks: {
        o: { a: 1, k: [
          { t: i * 25, s: [0], e: [90], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: i * 25 + 40, s: [90], e: [0], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 150, s: [0] }
        ]},
        r: { a: 0, k: 0 },
        p: { a: 1, k: [
          { t: i * 25, s: [130 + xOff, 85, 0], e: [130 + xOff + (i % 2 === 0 ? 8 : -8), 35, 0], i: { x: [0.2], y: [1] }, o: { x: [0.1], y: [0] } },
          { t: i * 25 + 75, s: [130 + xOff + (i % 2 === 0 ? 8 : -8), 35, 0] }
        ]},
        a: { a: 0, k: [0, 0, 0] },
        s: { a: 1, k: [
          { t: i * 25, s: [65, 65, 100], e: [130, 130, 100], i: { x: [0.2], y: [1] }, o: { x: [0.1], y: [0] } },
          { t: i * 25 + 75, s: [130, 130, 100] }
        ]}
      },
      ao: 0,
      shapes: [{
        ty: "gr",
        it: [
          {
            ty: "sh", d: 1,
            ks: {
              a: 0,
              k: {
                c: false,
                v: [[0, 18], [5, 9], [-5, -4], [0, -18]],
                i: [[0, 0], [-4, 4], [4, 4], [0, 0]],
                o: [[0, 0], [4, -4], [-4, -4], [0, 0]]
              }
            },
            nm: "Path"
          },
          { ty: "st", c: { a: 0, k: makeColor("#FFFFFF") }, o: { a: 0, k: 80 }, w: { a: 0, k: 3.2 }, lc: 2, lj: 2, nm: "Stroke" },
          makeTr()
        ],
        nm: "SteamGroup"
      }],
      ip: 0, op: 150, st: 0, bm: 0
    });
  }

  // Layer 9: Official Logo Graphic
  l.layers.push({
    ddd: 0, ind: 11, ty: 2, nm: "Official Logo Graphic", cl: "png", refId: "official_logo", sr: 1,
    ks: {
      o: { a: 0, k: 100 },
      r: { a: 0, k: 0 },
      p: { a: 1, k: [
        { t: 0, s: [130, 130, 0], e: [130, 122, 0], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
        { t: 75, s: [130, 122, 0], e: [130, 130, 0], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
        { t: 150, s: [130, 130, 0] }
      ]},
      a: { a: 0, k: [250, 250, 0] },
      s: { a: 1, k: [
        { t: 0, s: [39, 39, 100], e: [41, 41, 100], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
        { t: 75, s: [41, 41, 100], e: [39, 39, 100], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
        { t: 150, s: [39, 39, 100] }
      ]}
    },
    ip: 0, op: 150, st: 0, bm: 0
  });

  return l;
}

// ── 2. CLOCHE IDLE (START ORDER BUTTON) ──
function buildClocheIdle() {
  const l = baseLottie("Cloche Idle", 100, 100, 120, 60);

  // Steam wisp 1
  l.layers.push({
    ddd: 0,
    ind: 1,
    ty: 4,
    nm: "Steam Left",
    sr: 1,
    ks: {
      o: {
        a: 1,
        k: [
          { t: 0, s: [20], e: [90], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 60, s: [90], e: [20], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 120, s: [20] }
        ]
      },
      r: { a: 0, k: 0 },
      p: {
        a: 1,
        k: [
          { t: 0, s: [42, 36, 0], e: [45, 22, 0], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 60, s: [45, 22, 0], e: [42, 36, 0], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 120, s: [42, 36, 0] }
        ]
      },
      a: { a: 0, k: [0, 0, 0] },
      s: { a: 0, k: [100, 100, 100] }
    },
    ao: 0,
    shapes: [
      {
        ty: "gr",
        it: [
          {
            ty: "sh",
            d: 1,
            ks: {
              a: 0,
              k: {
                c: false,
                v: [[0, 12], [3, 4], [-3, -4], [0, -12]],
                i: [[0, 0], [-2, 2], [2, 2], [0, 0]],
                o: [[0, 0], [2, -2], [-2, -2], [0, 0]]
              }
            },
            nm: "W"
          },
          { ty: "st", c: { a: 0, k: makeColor("#FFFFFF") }, o: { a: 0, k: 90 }, w: { a: 0, k: 2.6 }, lc: 2, lj: 2, nm: "S" },
          makeTr()
        ],
        nm: "G"
      }
    ],
    ip: 0,
    op: 120,
    st: 0,
    bm: 0
  });

  // Steam wisp 2
  l.layers.push({
    ddd: 0,
    ind: 2,
    ty: 4,
    nm: "Steam Right",
    sr: 1,
    ks: {
      o: {
        a: 1,
        k: [
          { t: 0, s: [80], e: [20], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 60, s: [20], e: [80], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 120, s: [80] }
        ]
      },
      r: { a: 0, k: 0 },
      p: {
        a: 1,
        k: [
          { t: 0, s: [58, 24, 0], e: [55, 38, 0], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 60, s: [55, 38, 0], e: [58, 24, 0], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 120, s: [58, 24, 0] }
        ]
      },
      a: { a: 0, k: [0, 0, 0] },
      s: { a: 0, k: [100, 100, 100] }
    },
    ao: 0,
    shapes: [
      {
        ty: "gr",
        it: [
          {
            ty: "sh",
            d: 1,
            ks: {
              a: 0,
              k: {
                c: false,
                v: [[0, 12], [-3, 4], [3, -4], [0, -12]],
                i: [[0, 0], [2, 2], [-2, 2], [0, 0]],
                o: [[0, 0], [-2, -2], [2, -2], [0, 0]]
              }
            },
            nm: "W2"
          },
          { ty: "st", c: { a: 0, k: makeColor("#FFFFFF") }, o: { a: 0, k: 90 }, w: { a: 0, k: 2.6 }, lc: 2, lj: 2, nm: "S2" },
          makeTr()
        ],
        nm: "G2"
      }
    ],
    ip: 0,
    op: 120,
    st: 0,
    bm: 0
  });

  // Cloche Dome with smooth gentle float
  l.layers.push({
    ddd: 0,
    ind: 3,
    ty: 4,
    nm: "Cloche Dome",
    sr: 1,
    ks: {
      o: { a: 0, k: 100 },
      r: {
        a: 1,
        k: [
          { t: 0, s: [0], e: [1.8], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 60, s: [1.8], e: [0], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 120, s: [0] }
        ]
      },
      p: {
        a: 1,
        k: [
          { t: 0, s: [50, 50, 0], e: [50, 46, 0], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 60, s: [50, 46, 0], e: [50, 50, 0], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 120, s: [50, 50, 0] }
        ]
      },
      a: { a: 0, k: [0, 0, 0] },
      s: { a: 0, k: [100, 100, 100] }
    },
    ao: 0,
    shapes: [
      {
        ty: "gr",
        it: [
          { ty: "el", d: 1, p: { a: 0, k: [0, -25] }, s: { a: 0, k: [9, 9] }, nm: "Loop" },
          { ty: "st", c: { a: 0, k: makeColor("#FFFFFF") }, o: { a: 0, k: 100 }, w: { a: 0, k: 3 }, lc: 2, lj: 2, nm: "LSt" },
          {
            ty: "sh",
            d: 1,
            ks: {
              a: 0,
              k: {
                c: true,
                v: [[-26, 4], [26, 4], [26, 1], [0, -21], [-26, 1]],
                i: [[0, 0], [0, 0], [0, 0], [16, 0], [0, -11]],
                o: [[0, 0], [0, 0], [0, -11], [-16, 0], [0, 0]]
              }
            },
            nm: "DPath"
          },
          { ty: "fl", c: { a: 0, k: makeColor("#FFFFFF") }, o: { a: 0, k: 100 }, r: 1, nm: "DFill" },
          makeTr()
        ],
        nm: "Dome"
      }
    ],
    ip: 0,
    op: 120,
    st: 0,
    bm: 0
  });

  // Tray
  l.layers.push({
    ddd: 0,
    ind: 4,
    ty: 4,
    nm: "Tray",
    sr: 1,
    ks: {
      o: { a: 0, k: 100 },
      r: { a: 0, k: 0 },
      p: { a: 0, k: [50, 56, 0] },
      a: { a: 0, k: [0, 0, 0] },
      s: { a: 0, k: [100, 100, 100] }
    },
    ao: 0,
    shapes: [
      {
        ty: "gr",
        it: [
          { ty: "rc", d: 1, p: { a: 0, k: [0, 0] }, s: { a: 0, k: [64, 5] }, r: { a: 0, k: 2.5 }, nm: "TrayR" },
          { ty: "fl", c: { a: 0, k: makeColor("#FFFFFF") }, o: { a: 0, k: 100 }, r: 1, nm: "TFill" },
          makeTr()
        ],
        nm: "TrayG"
      }
    ],
    ip: 0,
    op: 120,
    st: 0,
    bm: 0
  });

  return l;
}

// ── 3. ICON PACKAGE (Quick Options) ──
function buildIconPackage() {
  const l = baseLottie("Package Icon", 100, 100, 60, 60);

  // Lid layer
  l.layers.push({
    ddd: 0,
    ind: 1,
    ty: 4,
    nm: "Lid",
    sr: 1,
    ks: {
      o: { a: 0, k: 100 },
      r: {
        a: 1,
        k: [
          { t: 0, s: [0], e: [-18], i: { x: [0.2], y: [1] }, o: { x: [0.1], y: [0] } },
          { t: 25, s: [-18], e: [0], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 60, s: [0] }
        ]
      },
      p: {
        a: 1,
        k: [
          { t: 0, s: [50, 42, 0], e: [46, 32, 0], i: { x: [0.2], y: [1] }, o: { x: [0.1], y: [0] } },
          { t: 25, s: [46, 32, 0], e: [50, 42, 0], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 60, s: [50, 42, 0] }
        ]
      },
      a: { a: 0, k: [-22, 0, 0] },
      s: { a: 0, k: [100, 100, 100] }
    },
    ao: 0,
    shapes: [
      {
        ty: "gr",
        it: [
          { ty: "rc", d: 1, p: { a: 0, k: [0, 0] }, s: { a: 0, k: [46, 8] }, r: { a: 0, k: 3 }, nm: "LidBar" },
          { ty: "fl", c: { a: 0, k: makeColor("#E11D48") }, o: { a: 0, k: 100 }, r: 1, nm: "LidF" },
          // Ribbon loop on top
          { ty: "el", d: 1, p: { a: 0, k: [0, -6] }, s: { a: 0, k: [10, 8] }, nm: "Ribbon" },
          { ty: "st", c: { a: 0, k: makeColor("#F59E0B") }, o: { a: 0, k: 100 }, w: { a: 0, k: 2.5 }, lc: 2, lj: 2, nm: "RSt" },
          makeTr()
        ],
        nm: "LidG"
      }
    ],
    ip: 0,
    op: 60,
    st: 0,
    bm: 0
  });

  // Box body
  l.layers.push({
    ddd: 0,
    ind: 2,
    ty: 4,
    nm: "Box Body",
    sr: 1,
    ks: {
      o: { a: 0, k: 100 },
      r: { a: 0, k: 0 },
      p: { a: 0, k: [50, 58, 0] },
      a: { a: 0, k: [0, 0, 0] },
      s: {
        a: 1,
        k: [
          { t: 0, s: [100, 100, 100], e: [104, 96, 100], i: { x: [0.2], y: [1] }, o: { x: [0.1], y: [0] } },
          { t: 25, s: [104, 96, 100], e: [100, 100, 100], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 60, s: [100, 100, 100] }
        ]
      }
    },
    ao: 0,
    shapes: [
      {
        ty: "gr",
        it: [
          { ty: "rc", d: 1, p: { a: 0, k: [0, 0] }, s: { a: 0, k: [40, 28] }, r: { a: 0, k: 4 }, nm: "BodyR" },
          { ty: "fl", c: { a: 0, k: makeColor("#FFF1F2") }, o: { a: 0, k: 100 }, r: 1, nm: "BodyF" },
          { ty: "st", c: { a: 0, k: makeColor("#E11D48") }, o: { a: 0, k: 100 }, w: { a: 0, k: 3 }, lc: 2, lj: 2, nm: "BodySt" },
          // Ribbon vertical
          { ty: "rc", d: 1, p: { a: 0, k: [0, 0] }, s: { a: 0, k: [6, 28] }, r: { a: 0, k: 0 }, nm: "RibbonV" },
          { ty: "fl", c: { a: 0, k: makeColor("#F59E0B") }, o: { a: 0, k: 100 }, r: 1, nm: "RibbonF" },
          makeTr()
        ],
        nm: "BodyG"
      }
    ],
    ip: 0,
    op: 60,
    st: 0,
    bm: 0
  });

  return l;
}

// ── 4. ICON CALENDAR (Event Types & Easy Booking) ──
function buildIconCalendar() {
  const l = baseLottie("Calendar Icon", 100, 100, 60, 60);

  // Flip page
  l.layers.push({
    ddd: 0,
    ind: 1,
    ty: 4,
    nm: "Flipping Page",
    sr: 1,
    ks: {
      o: { a: 0, k: 100 },
      r: { a: 0, k: 0 },
      p: { a: 0, k: [50, 52, 0] },
      a: { a: 0, k: [0, -18, 0] },
      s: {
        a: 1,
        k: [
          { t: 0, s: [100, 100, 100], e: [100, -80, 100], i: { x: [0.2], y: [1] }, o: { x: [0.1], y: [0] } },
          { t: 30, s: [100, -80, 100], e: [100, 100, 100], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 60, s: [100, 100, 100] }
        ]
      }
    },
    ao: 0,
    shapes: [
      {
        ty: "gr",
        it: [
          { ty: "rc", d: 1, p: { a: 0, k: [0, 4] }, s: { a: 0, k: [40, 24] }, r: { a: 0, k: 3 }, nm: "PageR" },
          { ty: "fl", c: { a: 0, k: makeColor("#FFF1F2") }, o: { a: 0, k: 100 }, r: 1, nm: "PageF" },
          { ty: "st", c: { a: 0, k: makeColor("#E11D48") }, o: { a: 0, k: 60 }, w: { a: 0, k: 2 }, lc: 2, lj: 2, nm: "PageSt" },
          makeTr()
        ],
        nm: "PageG"
      }
    ],
    ip: 0,
    op: 60,
    st: 0,
    bm: 0
  });

  // Calendar Base
  l.layers.push({
    ddd: 0,
    ind: 2,
    ty: 4,
    nm: "Calendar Frame",
    sr: 1,
    ks: {
      o: { a: 0, k: 100 },
      r: {
        a: 1,
        k: [
          { t: 0, s: [0], e: [4], i: { x: [0.2], y: [1] }, o: { x: [0.1], y: [0] } },
          { t: 25, s: [4], e: [0], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 60, s: [0] }
        ]
      },
      p: { a: 0, k: [50, 52, 0] },
      a: { a: 0, k: [0, 0, 0] },
      s: { a: 0, k: [100, 100, 100] }
    },
    ao: 0,
    shapes: [
      {
        ty: "gr",
        it: [
          // Header bar
          { ty: "rc", d: 1, p: { a: 0, k: [0, -14] }, s: { a: 0, k: [44, 10] }, r: { a: 0, k: 4 }, nm: "HeaderR" },
          { ty: "fl", c: { a: 0, k: makeColor("#E11D48") }, o: { a: 0, k: 100 }, r: 1, nm: "HeaderF" },
          // Sheet
          { ty: "rc", d: 1, p: { a: 0, k: [0, 5] }, s: { a: 0, k: [44, 28] }, r: { a: 0, k: 4 }, nm: "SheetR" },
          { ty: "st", c: { a: 0, k: makeColor("#E11D48") }, o: { a: 0, k: 100 }, w: { a: 0, k: 3 }, lc: 2, lj: 2, nm: "SheetSt" },
          // Binder pins
          { ty: "el", d: 1, p: { a: 0, k: [-10, -18] }, s: { a: 0, k: [5, 7] }, nm: "Pin1" },
          { ty: "fl", c: { a: 0, k: makeColor("#F59E0B") }, o: { a: 0, k: 100 }, r: 1, nm: "PinF1" },
          { ty: "el", d: 1, p: { a: 0, k: [10, -18] }, s: { a: 0, k: [5, 7] }, nm: "Pin2" },
          { ty: "fl", c: { a: 0, k: makeColor("#F59E0B") }, o: { a: 0, k: 100 }, r: 1, nm: "PinF2" },
          makeTr()
        ],
        nm: "CalG"
      }
    ],
    ip: 0,
    op: 60,
    st: 0,
    bm: 0
  });

  return l;
}

// ── 5. ICON UTENSILS (Add-ons) ──
function buildIconUtensils() {
  const l = baseLottie("Utensils Icon", 100, 100, 60, 60);

  // Fork (rotates)
  l.layers.push({
    ddd: 0,
    ind: 1,
    ty: 4,
    nm: "Fork",
    sr: 1,
    ks: {
      o: { a: 0, k: 100 },
      r: {
        a: 1,
        k: [
          { t: 0, s: [-25], e: [-45], i: { x: [0.2], y: [1] }, o: { x: [0.1], y: [0] } },
          { t: 30, s: [-45], e: [-25], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 60, s: [-25] }
        ]
      },
      p: { a: 0, k: [50, 50, 0] },
      a: { a: 0, k: [0, 0, 0] },
      s: { a: 0, k: [100, 100, 100] }
    },
    ao: 0,
    shapes: [
      {
        ty: "gr",
        it: [
          { ty: "rc", d: 1, p: { a: 0, k: [0, 6] }, s: { a: 0, k: [4, 30] }, r: { a: 0, k: 2 }, nm: "Handle" },
          { ty: "fl", c: { a: 0, k: makeColor("#E11D48") }, o: { a: 0, k: 100 }, r: 1, nm: "HF" },
          {
            ty: "sh",
            d: 1,
            ks: {
              a: 0,
              k: {
                c: true,
                v: [[-6, -8], [-6, -20], [-2, -20], [-2, -12], [2, -12], [2, -20], [6, -20], [6, -8]],
                i: [[0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0]],
                o: [[0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0]]
              }
            },
            nm: "Prongs"
          },
          { ty: "fl", c: { a: 0, k: makeColor("#E11D48") }, o: { a: 0, k: 100 }, r: 1, nm: "PF" },
          makeTr()
        ],
        nm: "ForkG"
      }
    ],
    ip: 0,
    op: 60,
    st: 0,
    bm: 0
  });

  // Knife (rotates opposite)
  l.layers.push({
    ddd: 0,
    ind: 2,
    ty: 4,
    nm: "Knife",
    sr: 1,
    ks: {
      o: { a: 0, k: 100 },
      r: {
        a: 1,
        k: [
          { t: 0, s: [25], e: [45], i: { x: [0.2], y: [1] }, o: { x: [0.1], y: [0] } },
          { t: 30, s: [45], e: [25], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 60, s: [25] }
        ]
      },
      p: { a: 0, k: [50, 50, 0] },
      a: { a: 0, k: [0, 0, 0] },
      s: { a: 0, k: [100, 100, 100] }
    },
    ao: 0,
    shapes: [
      {
        ty: "gr",
        it: [
          { ty: "rc", d: 1, p: { a: 0, k: [0, 6] }, s: { a: 0, k: [4, 30] }, r: { a: 0, k: 2 }, nm: "KHandle" },
          { ty: "fl", c: { a: 0, k: makeColor("#F59E0B") }, o: { a: 0, k: 100 }, r: 1, nm: "KHF" },
          {
            ty: "sh",
            d: 1,
            ks: {
              a: 0,
              k: {
                c: true,
                v: [[-2, -8], [-2, -22], [4, -14], [4, -8]],
                i: [[0, 0], [0, 0], [0, 0], [0, 0]],
                o: [[0, 0], [0, 0], [0, 0], [0, 0]]
              }
            },
            nm: "Blade"
          },
          { ty: "fl", c: { a: 0, k: makeColor("#F59E0B") }, o: { a: 0, k: 100 }, r: 1, nm: "BF" },
          makeTr()
        ],
        nm: "KnifeG"
      }
    ],
    ip: 0,
    op: 60,
    st: 0,
    bm: 0
  });

  return l;
}

// ── 6. ICON FILETEXT (View Orders) ──
function buildIconFileText() {
  const l = baseLottie("Orders FileText Icon", 100, 100, 60, 60);

  l.layers.push({
    ddd: 0,
    ind: 1,
    ty: 4,
    nm: "Document",
    sr: 1,
    ks: {
      o: { a: 0, k: 100 },
      r: { a: 0, k: 0 },
      p: { a: 0, k: [50, 50, 0] },
      a: { a: 0, k: [0, 0, 0] },
      s: {
        a: 1,
        k: [
          { t: 0, s: [100, 100, 100], e: [106, 106, 100], i: { x: [0.2], y: [1] }, o: { x: [0.1], y: [0] } },
          { t: 30, s: [106, 106, 100], e: [100, 100, 100], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 60, s: [100, 100, 100] }
        ]
      }
    },
    ao: 0,
    shapes: [
      {
        ty: "gr",
        it: [
          // Sheet
          { ty: "rc", d: 1, p: { a: 0, k: [0, 0] }, s: { a: 0, k: [38, 48] }, r: { a: 0, k: 4 }, nm: "Sheet" },
          { ty: "st", c: { a: 0, k: makeColor("#E11D48") }, o: { a: 0, k: 100 }, w: { a: 0, k: 3 }, lc: 2, lj: 2, nm: "SSt" },
          { ty: "fl", c: { a: 0, k: makeColor("#FFF1F2") }, o: { a: 0, k: 80 }, r: 1, nm: "SFill" },
          // Text lines
          { ty: "rc", d: 1, p: { a: 0, k: [0, -10] }, s: { a: 0, k: [22, 3] }, r: { a: 0, k: 1.5 }, nm: "L1" },
          { ty: "fl", c: { a: 0, k: makeColor("#E11D48") }, o: { a: 0, k: 100 }, r: 1, nm: "L1F" },
          { ty: "rc", d: 1, p: { a: 0, k: [0, -2] }, s: { a: 0, k: [22, 3] }, r: { a: 0, k: 1.5 }, nm: "L2" },
          { ty: "fl", c: { a: 0, k: makeColor("#E11D48") }, o: { a: 0, k: 100 }, r: 1, nm: "L2F" },
          { ty: "rc", d: 1, p: { a: 0, k: [-4, 6] }, s: { a: 0, k: [14, 3] }, r: { a: 0, k: 1.5 }, nm: "L3" },
          { ty: "fl", c: { a: 0, k: makeColor("#F59E0B") }, o: { a: 0, k: 100 }, r: 1, nm: "L3F" },
          makeTr()
        ],
        nm: "DocG"
      }
    ],
    ip: 0,
    op: 60,
    st: 0,
    bm: 0
  });

  return l;
}

// ── 7. ICON SHIELD CHECK (Fresh & Quality) ──
function buildIconShieldCheck() {
  const l = baseLottie("Shield Check Icon", 100, 100, 80, 60);

  // Checkmark pulse
  l.layers.push({
    ddd: 0,
    ind: 1,
    ty: 4,
    nm: "Check",
    sr: 1,
    ks: {
      o: { a: 0, k: 100 },
      r: { a: 0, k: 0 },
      p: { a: 0, k: [50, 50, 0] },
      a: { a: 0, k: [0, 0, 0] },
      s: {
        a: 1,
        k: [
          { t: 0, s: [100, 100, 100], e: [120, 120, 100], i: { x: [0.2], y: [1] }, o: { x: [0.1], y: [0] } },
          { t: 40, s: [120, 120, 100], e: [100, 100, 100], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 80, s: [100, 100, 100] }
        ]
      }
    },
    ao: 0,
    shapes: [
      {
        ty: "gr",
        it: [
          {
            ty: "sh",
            d: 1,
            ks: {
              a: 0,
              k: {
                c: false,
                v: [[-9, 0], [-3, 6], [9, -6]],
                i: [[0, 0], [0, 0], [0, 0]],
                o: [[0, 0], [0, 0], [0, 0]]
              }
            },
            nm: "CheckPath"
          },
          { ty: "st", c: { a: 0, k: makeColor("#10B981") }, o: { a: 0, k: 100 }, w: { a: 0, k: 4 }, lc: 2, lj: 2, nm: "CSt" },
          makeTr()
        ],
        nm: "CheckG"
      }
    ],
    ip: 0,
    op: 80,
    st: 0,
    bm: 0
  });

  // Shield
  l.layers.push({
    ddd: 0,
    ind: 2,
    ty: 4,
    nm: "Shield",
    sr: 1,
    ks: {
      o: { a: 0, k: 100 },
      r: { a: 0, k: 0 },
      p: { a: 0, k: [50, 50, 0] },
      a: { a: 0, k: [0, 0, 0] },
      s: { a: 0, k: [100, 100, 100] }
    },
    ao: 0,
    shapes: [
      {
        ty: "gr",
        it: [
          {
            ty: "sh",
            d: 1,
            ks: {
              a: 0,
              k: {
                c: true,
                v: [[-22, -20], [22, -20], [22, 4], [0, 24], [-22, 4]],
                i: [[0, 0], [0, 0], [0, 0], [12, -4], [-12, -4]],
                o: [[0, 0], [0, 0], [0, 12], [0, 0], [0, 0]]
              }
            },
            nm: "ShieldP"
          },
          { ty: "st", c: { a: 0, k: makeColor("#E11D48") }, o: { a: 0, k: 100 }, w: { a: 0, k: 3.5 }, lc: 2, lj: 2, nm: "SSt" },
          { ty: "fl", c: { a: 0, k: makeColor("#FFF1F2") }, o: { a: 0, k: 85 }, r: 1, nm: "SFill" },
          makeTr()
        ],
        nm: "ShieldG"
      }
    ],
    ip: 0,
    op: 80,
    st: 0,
    bm: 0
  });

  return l;
}

// ── 8. ICON USERS (Trusted Service) ──
function buildIconUsers() {
  const l = baseLottie("Users Icon", 100, 100, 80, 60);

  // Left Avatar
  l.layers.push({
    ddd: 0,
    ind: 1,
    ty: 4,
    nm: "User 1",
    sr: 1,
    ks: {
      o: { a: 0, k: 100 },
      r: { a: 0, k: 0 },
      p: {
        a: 1,
        k: [
          { t: 0, s: [42, 50, 0], e: [42, 46, 0], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 40, s: [42, 46, 0], e: [42, 50, 0], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 80, s: [42, 50, 0] }
        ]
      },
      a: { a: 0, k: [0, 0, 0] },
      s: { a: 0, k: [100, 100, 100] }
    },
    ao: 0,
    shapes: [
      {
        ty: "gr",
        it: [
          { ty: "el", d: 1, p: { a: 0, k: [0, -8] }, s: { a: 0, k: [16, 16] }, nm: "Head" },
          { ty: "fl", c: { a: 0, k: makeColor("#E11D48") }, o: { a: 0, k: 100 }, r: 1, nm: "HF" },
          { ty: "el", d: 1, p: { a: 0, k: [0, 14] }, s: { a: 0, k: [28, 16] }, nm: "Body" },
          { ty: "fl", c: { a: 0, k: makeColor("#E11D48") }, o: { a: 0, k: 90 }, r: 1, nm: "BF" },
          makeTr()
        ],
        nm: "User1G"
      }
    ],
    ip: 0,
    op: 80,
    st: 0,
    bm: 0
  });

  // Right Avatar
  l.layers.push({
    ddd: 0,
    ind: 2,
    ty: 4,
    nm: "User 2",
    sr: 1,
    ks: {
      o: { a: 0, k: 90 },
      r: { a: 0, k: 0 },
      p: {
        a: 1,
        k: [
          { t: 0, s: [62, 48, 0], e: [62, 52, 0], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 40, s: [62, 52, 0], e: [62, 48, 0], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 80, s: [62, 48, 0] }
        ]
      },
      a: { a: 0, k: [0, 0, 0] },
      s: { a: 0, k: [90, 90, 100] }
    },
    ao: 0,
    shapes: [
      {
        ty: "gr",
        it: [
          { ty: "el", d: 1, p: { a: 0, k: [0, -8] }, s: { a: 0, k: [14, 14] }, nm: "Head2" },
          { ty: "fl", c: { a: 0, k: makeColor("#F59E0B") }, o: { a: 0, k: 100 }, r: 1, nm: "HF2" },
          { ty: "el", d: 1, p: { a: 0, k: [0, 14] }, s: { a: 0, k: [26, 15] }, nm: "Body2" },
          { ty: "fl", c: { a: 0, k: makeColor("#F59E0B") }, o: { a: 0, k: 90 }, r: 1, nm: "BF2" },
          makeTr()
        ],
        nm: "User2G"
      }
    ],
    ip: 0,
    op: 80,
    st: 0,
    bm: 0
  });

  return l;
}

// ── 9. ICON LOCK (Secure & Private) ──
function buildIconLock() {
  const l = baseLottie("Lock Icon", 100, 100, 60, 60);

  // Shackle (slides up slightly on unlock loop)
  l.layers.push({
    ddd: 0,
    ind: 1,
    ty: 4,
    nm: "Shackle",
    sr: 1,
    ks: {
      o: { a: 0, k: 100 },
      r: { a: 0, k: 0 },
      p: {
        a: 1,
        k: [
          { t: 0, s: [50, 40, 0], e: [50, 34, 0], i: { x: [0.2], y: [1] }, o: { x: [0.1], y: [0] } },
          { t: 30, s: [50, 34, 0], e: [50, 40, 0], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 60, s: [50, 40, 0] }
        ]
      },
      a: { a: 0, k: [0, 0, 0] },
      s: { a: 0, k: [100, 100, 100] }
    },
    ao: 0,
    shapes: [
      {
        ty: "gr",
        it: [
          {
            ty: "sh",
            d: 1,
            ks: {
              a: 0,
              k: {
                c: false,
                v: [[-12, 10], [-12, -2], [12, -2], [12, 10]],
                i: [[0, 0], [0, -8], [0, -8], [0, 0]],
                o: [[0, -8], [0, 0], [0, 0], [0, 0]]
              }
            },
            nm: "ShackleP"
          },
          { ty: "st", c: { a: 0, k: makeColor("#F59E0B") }, o: { a: 0, k: 100 }, w: { a: 0, k: 4 }, lc: 2, lj: 2, nm: "SSt" },
          makeTr()
        ],
        nm: "ShackleG"
      }
    ],
    ip: 0,
    op: 60,
    st: 0,
    bm: 0
  });

  // Lock Body
  l.layers.push({
    ddd: 0,
    ind: 2,
    ty: 4,
    nm: "Body",
    sr: 1,
    ks: {
      o: { a: 0, k: 100 },
      r: { a: 0, k: 0 },
      p: { a: 0, k: [50, 58, 0] },
      a: { a: 0, k: [0, 0, 0] },
      s: { a: 0, k: [100, 100, 100] }
    },
    ao: 0,
    shapes: [
      {
        ty: "gr",
        it: [
          { ty: "rc", d: 1, p: { a: 0, k: [0, 0] }, s: { a: 0, k: [36, 26] }, r: { a: 0, k: 5 }, nm: "BodyR" },
          { ty: "fl", c: { a: 0, k: makeColor("#E11D48") }, o: { a: 0, k: 100 }, r: 1, nm: "BodyF" },
          // Keyhole
          { ty: "el", d: 1, p: { a: 0, k: [0, -2] }, s: { a: 0, k: [6, 6] }, nm: "KeyH" },
          { ty: "fl", c: { a: 0, k: makeColor("#FFFFFF") }, o: { a: 0, k: 100 }, r: 1, nm: "KF" },
          { ty: "rc", d: 1, p: { a: 0, k: [0, 3] }, s: { a: 0, k: [3, 6] }, r: { a: 0, k: 1 }, nm: "KeySlot" },
          { ty: "fl", c: { a: 0, k: makeColor("#FFFFFF") }, o: { a: 0, k: 100 }, r: 1, nm: "KSF" },
          makeTr()
        ],
        nm: "BodyG"
      }
    ],
    ip: 0,
    op: 60,
    st: 0,
    bm: 0
  });

  return l;
}

// ── 10. ICON THEME TOGGLE (Sun to Moon) ──
function buildIconThemeToggle() {
  const l = baseLottie("Theme Toggle Icon", 100, 100, 60, 60);

  l.layers.push({
    ddd: 0,
    ind: 1,
    ty: 4,
    nm: "Celestial Body",
    sr: 1,
    ks: {
      o: { a: 0, k: 100 },
      r: {
        a: 1,
        k: [
          { t: 0, s: [0], e: [180], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 60, s: [180] }
        ]
      },
      p: { a: 0, k: [50, 50, 0] },
      a: { a: 0, k: [0, 0, 0] },
      s: {
        a: 1,
        k: [
          { t: 0, s: [100, 100, 100], e: [115, 115, 100], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 30, s: [115, 115, 100], e: [100, 100, 100], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 60, s: [100, 100, 100] }
        ]
      }
    },
    ao: 0,
    shapes: [
      {
        ty: "gr",
        it: [
          // Sun core
          { ty: "el", d: 1, p: { a: 0, k: [0, 0] }, s: { a: 0, k: [22, 22] }, nm: "SunCore" },
          { ty: "fl", c: { a: 0, k: makeColor("#F59E0B") }, o: { a: 0, k: 100 }, r: 1, nm: "SunF" },
          // 4 rays
          { ty: "rc", d: 1, p: { a: 0, k: [0, -18] }, s: { a: 0, k: [3, 8] }, r: { a: 0, k: 1.5 }, nm: "R1" },
          { ty: "fl", c: { a: 0, k: makeColor("#F59E0B") }, o: { a: 0, k: 100 }, r: 1, nm: "R1F" },
          { ty: "rc", d: 1, p: { a: 0, k: [0, 18] }, s: { a: 0, k: [3, 8] }, r: { a: 0, k: 1.5 }, nm: "R2" },
          { ty: "fl", c: { a: 0, k: makeColor("#F59E0B") }, o: { a: 0, k: 100 }, r: 1, nm: "R2F" },
          { ty: "rc", d: 1, p: { a: 0, k: [-18, 0] }, s: { a: 0, k: [8, 3] }, r: { a: 0, k: 1.5 }, nm: "R3" },
          { ty: "fl", c: { a: 0, k: makeColor("#F59E0B") }, o: { a: 0, k: 100 }, r: 1, nm: "R3F" },
          { ty: "rc", d: 1, p: { a: 0, k: [18, 0] }, s: { a: 0, k: [8, 3] }, r: { a: 0, k: 1.5 }, nm: "R4" },
          { ty: "fl", c: { a: 0, k: makeColor("#F59E0B") }, o: { a: 0, k: 100 }, r: 1, nm: "R4F" },
          makeTr()
        ],
        nm: "SunG"
      }
    ],
    ip: 0,
    op: 60,
    st: 0,
    bm: 0
  });

  return l;
}

// ── 11. ICON FULLSCREEN ──
function buildIconFullscreen() {
  const l = baseLottie("Fullscreen Icon", 100, 100, 60, 60);

  l.layers.push({
    ddd: 0,
    ind: 1,
    ty: 4,
    nm: "Arrows",
    sr: 1,
    ks: {
      o: { a: 0, k: 100 },
      r: { a: 0, k: 0 },
      p: { a: 0, k: [50, 50, 0] },
      a: { a: 0, k: [0, 0, 0] },
      s: {
        a: 1,
        k: [
          { t: 0, s: [92, 92, 100], e: [115, 115, 100], i: { x: [0.2], y: [1] }, o: { x: [0.1], y: [0] } },
          { t: 30, s: [115, 115, 100], e: [92, 92, 100], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 60, s: [92, 92, 100] }
        ]
      }
    },
    ao: 0,
    shapes: [
      {
        ty: "gr",
        it: [
          // Top-left
          {
            ty: "sh",
            d: 1,
            ks: {
              a: 0,
              k: {
                c: false,
                v: [[-18, -10], [-18, -18], [-10, -18]],
                i: [[0, 0], [0, 0], [0, 0]],
                o: [[0, 0], [0, 0], [0, 0]]
              }
            },
            nm: "TL"
          },
          { ty: "st", c: { a: 0, k: makeColor("#E11D48") }, o: { a: 0, k: 100 }, w: { a: 0, k: 3.5 }, lc: 2, lj: 2, nm: "S1" },
          // Top-right
          {
            ty: "sh",
            d: 1,
            ks: {
              a: 0,
              k: {
                c: false,
                v: [[10, -18], [18, -18], [18, -10]],
                i: [[0, 0], [0, 0], [0, 0]],
                o: [[0, 0], [0, 0], [0, 0]]
              }
            },
            nm: "TR"
          },
          { ty: "st", c: { a: 0, k: makeColor("#E11D48") }, o: { a: 0, k: 100 }, w: { a: 0, k: 3.5 }, lc: 2, lj: 2, nm: "S2" },
          // Bottom-left
          {
            ty: "sh",
            d: 1,
            ks: {
              a: 0,
              k: {
                c: false,
                v: [[-18, 10], [-18, 18], [-10, 18]],
                i: [[0, 0], [0, 0], [0, 0]],
                o: [[0, 0], [0, 0], [0, 0]]
              }
            },
            nm: "BL"
          },
          { ty: "st", c: { a: 0, k: makeColor("#E11D48") }, o: { a: 0, k: 100 }, w: { a: 0, k: 3.5 }, lc: 2, lj: 2, nm: "S3" },
          // Bottom-right
          {
            ty: "sh",
            d: 1,
            ks: {
              a: 0,
              k: {
                c: false,
                v: [[10, 18], [18, 18], [18, 10]],
                i: [[0, 0], [0, 0], [0, 0]],
                o: [[0, 0], [0, 0], [0, 0]]
              }
            },
            nm: "BR"
          },
          { ty: "st", c: { a: 0, k: makeColor("#E11D48") }, o: { a: 0, k: 100 }, w: { a: 0, k: 3.5 }, lc: 2, lj: 2, nm: "S4" },
          makeTr()
        ],
        nm: "ArrowsG"
      }
    ],
    ip: 0,
    op: 60,
    st: 0,
    bm: 0
  });

  return l;
}

// ── 12. ICON SETTINGS GEAR ──
function buildIconSettingsGear() {
  const l = baseLottie("Settings Gear Icon", 100, 100, 60, 60);

  l.layers.push({
    ddd: 0,
    ind: 1,
    ty: 4,
    nm: "Gear",
    sr: 1,
    ks: {
      o: { a: 0, k: 100 },
      r: {
        a: 1,
        k: [
          { t: 0, s: [0], e: [180], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 60, s: [180] }
        ]
      },
      p: { a: 0, k: [50, 50, 0] },
      a: { a: 0, k: [0, 0, 0] },
      s: { a: 0, k: [100, 100, 100] }
    },
    ao: 0,
    shapes: [
      {
        ty: "gr",
        it: [
          // Center hole
          { ty: "el", d: 1, p: { a: 0, k: [0, 0] }, s: { a: 0, k: [14, 14] }, nm: "Hole" },
          { ty: "st", c: { a: 0, k: makeColor("#E11D48") }, o: { a: 0, k: 100 }, w: { a: 0, k: 4 }, lc: 2, lj: 2, nm: "HoleSt" },
          // Ring body
          { ty: "el", d: 1, p: { a: 0, k: [0, 0] }, s: { a: 0, k: [28, 28] }, nm: "Ring" },
          { ty: "st", c: { a: 0, k: makeColor("#E11D48") }, o: { a: 0, k: 100 }, w: { a: 0, k: 6 }, lc: 2, lj: 2, nm: "RingSt" },
          // 4 cross cogs
          { ty: "rc", d: 1, p: { a: 0, k: [0, 0] }, s: { a: 0, k: [38, 7] }, r: { a: 0, k: 2 }, nm: "Cog1" },
          { ty: "fl", c: { a: 0, k: makeColor("#E11D48") }, o: { a: 0, k: 100 }, r: 1, nm: "Cog1F" },
          { ty: "rc", d: 1, p: { a: 0, k: [0, 0] }, s: { a: 0, k: [7, 38] }, r: { a: 0, k: 2 }, nm: "Cog2" },
          { ty: "fl", c: { a: 0, k: makeColor("#E11D48") }, o: { a: 0, k: 100 }, r: 1, nm: "Cog2F" },
          makeTr()
        ],
        nm: "GearG"
      }
    ],
    ip: 0,
    op: 60,
    st: 0,
    bm: 0
  });

  return l;
}

// ── 13. EMPTY STATE (Plate with Steam) ──
function buildEmptyPlate() {
  const l = baseLottie("Empty Plate", 140, 140, 100, 60);

  // Steam lines
  l.layers.push({
    ddd: 0,
    ind: 1,
    ty: 4,
    nm: "Aroma Steam",
    sr: 1,
    ks: {
      o: {
        a: 1,
        k: [
          { t: 0, s: [30], e: [90], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 50, s: [90], e: [30], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 100, s: [30] }
        ]
      },
      r: { a: 0, k: 0 },
      p: {
        a: 1,
        k: [
          { t: 0, s: [70, 52, 0], e: [70, 42, 0], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 50, s: [70, 42, 0], e: [70, 52, 0], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 100, s: [70, 52, 0] }
        ]
      },
      a: { a: 0, k: [0, 0, 0] },
      s: { a: 0, k: [100, 100, 100] }
    },
    ao: 0,
    shapes: [
      {
        ty: "gr",
        it: [
          {
            ty: "sh",
            d: 1,
            ks: {
              a: 0,
              k: {
                c: false,
                v: [[-10, 10], [-6, 0], [-14, -10]],
                i: [[0, 0], [-3, 3], [0, 0]],
                o: [[0, 0], [3, -3], [0, 0]]
              }
            },
            nm: "S1"
          },
          { ty: "st", c: { a: 0, k: makeColor("#F59E0B") }, o: { a: 0, k: 80 }, w: { a: 0, k: 2.5 }, lc: 2, lj: 2, nm: "St1" },
          {
            ty: "sh",
            d: 1,
            ks: {
              a: 0,
              k: {
                c: false,
                v: [[8, 10], [12, 0], [6, -10]],
                i: [[0, 0], [3, 3], [0, 0]],
                o: [[0, 0], [-3, -3], [0, 0]]
              }
            },
            nm: "S2"
          },
          { ty: "st", c: { a: 0, k: makeColor("#F59E0B") }, o: { a: 0, k: 80 }, w: { a: 0, k: 2.5 }, lc: 2, lj: 2, nm: "St2" },
          makeTr()
        ],
        nm: "SteamG"
      }
    ],
    ip: 0,
    op: 100,
    st: 0,
    bm: 0
  });

  // Plate
  l.layers.push({
    ddd: 0,
    ind: 2,
    ty: 4,
    nm: "Serving Plate",
    sr: 1,
    ks: {
      o: { a: 0, k: 100 },
      r: { a: 0, k: 0 },
      p: { a: 0, k: [70, 78, 0] },
      a: { a: 0, k: [0, 0, 0] },
      s: { a: 0, k: [100, 100, 100] }
    },
    ao: 0,
    shapes: [
      {
        ty: "gr",
        it: [
          // Outer Rim
          { ty: "el", d: 1, p: { a: 0, k: [0, 0] }, s: { a: 0, k: [76, 42] }, nm: "OuterRim" },
          { ty: "st", c: { a: 0, k: makeColor("#E11D48") }, o: { a: 0, k: 100 }, w: { a: 0, k: 3.5 }, lc: 2, lj: 2, nm: "ORSt" },
          { ty: "fl", c: { a: 0, k: makeColor("#FFF1F2") }, o: { a: 0, k: 100 }, r: 1, nm: "ORFill" },
          // Inner Well
          { ty: "el", d: 1, p: { a: 0, k: [0, 0] }, s: { a: 0, k: [52, 28] }, nm: "InnerWell" },
          { ty: "st", c: { a: 0, k: makeColor("#E11D48") }, o: { a: 0, k: 50 }, w: { a: 0, k: 2 }, lc: 2, lj: 2, nm: "IWSt" },
          makeTr()
        ],
        nm: "PlateG"
      }
    ],
    ip: 0,
    op: 100,
    st: 0,
    bm: 0
  });

  return l;
}

// ── 14. TOAST SUCCESS ──
function buildToastSuccess() {
  const l = baseLottie("Toast Success", 80, 80, 50, 60);

  l.layers.push({
    ddd: 0,
    ind: 1,
    ty: 4,
    nm: "Check Circle",
    sr: 1,
    ks: {
      o: { a: 0, k: 100 },
      r: { a: 0, k: 0 },
      p: { a: 0, k: [40, 40, 0] },
      a: { a: 0, k: [0, 0, 0] },
      s: {
        a: 1,
        k: [
          { t: 0, s: [30, 30, 100], e: [115, 115, 100], i: { x: [0.2], y: [1] }, o: { x: [0.1], y: [0] } },
          { t: 25, s: [115, 115, 100], e: [100, 100, 100], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 50, s: [100, 100, 100] }
        ]
      }
    },
    ao: 0,
    shapes: [
      {
        ty: "gr",
        it: [
          { ty: "el", d: 1, p: { a: 0, k: [0, 0] }, s: { a: 0, k: [42, 42] }, nm: "Circle" },
          { ty: "fl", c: { a: 0, k: makeColor("#10B981") }, o: { a: 0, k: 100 }, r: 1, nm: "CFill" },
          {
            ty: "sh",
            d: 1,
            ks: {
              a: 0,
              k: {
                c: false,
                v: [[-8, 0], [-2, 6], [8, -5]],
                i: [[0, 0], [0, 0], [0, 0]],
                o: [[0, 0], [0, 0], [0, 0]]
              }
            },
            nm: "Checkmark"
          },
          { ty: "st", c: { a: 0, k: makeColor("#FFFFFF") }, o: { a: 0, k: 100 }, w: { a: 0, k: 3.5 }, lc: 2, lj: 2, nm: "CSt" },
          makeTr()
        ],
        nm: "SuccessG"
      }
    ],
    ip: 0,
    op: 50,
    st: 0,
    bm: 0
  });

  return l;
}

// ── 15. TOAST INFO ──
function buildToastInfo() {
  const l = baseLottie("Toast Info", 80, 80, 50, 60);

  l.layers.push({
    ddd: 0,
    ind: 1,
    ty: 4,
    nm: "Info Circle",
    sr: 1,
    ks: {
      o: { a: 0, k: 100 },
      r: { a: 0, k: 0 },
      p: { a: 0, k: [40, 40, 0] },
      a: { a: 0, k: [0, 0, 0] },
      s: {
        a: 1,
        k: [
          { t: 0, s: [30, 30, 100], e: [115, 115, 100], i: { x: [0.2], y: [1] }, o: { x: [0.1], y: [0] } },
          { t: 25, s: [115, 115, 100], e: [100, 100, 100], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 50, s: [100, 100, 100] }
        ]
      }
    },
    ao: 0,
    shapes: [
      {
        ty: "gr",
        it: [
          { ty: "el", d: 1, p: { a: 0, k: [0, 0] }, s: { a: 0, k: [42, 42] }, nm: "Circle" },
          { ty: "fl", c: { a: 0, k: makeColor("#3B82F6") }, o: { a: 0, k: 100 }, r: 1, nm: "IFill" },
          // Dot of 'i'
          { ty: "el", d: 1, p: { a: 0, k: [0, -7] }, s: { a: 0, k: [4.5, 4.5] }, nm: "IDot" },
          { ty: "fl", c: { a: 0, k: makeColor("#FFFFFF") }, o: { a: 0, k: 100 }, r: 1, nm: "IDotF" },
          // Stem of 'i'
          { ty: "rc", d: 1, p: { a: 0, k: [0, 3] }, s: { a: 0, k: [3.8, 11] }, r: { a: 0, k: 1.8 }, nm: "IStem" },
          { ty: "fl", c: { a: 0, k: makeColor("#FFFFFF") }, o: { a: 0, k: 100 }, r: 1, nm: "IStemF" },
          makeTr()
        ],
        nm: "InfoG"
      }
    ],
    ip: 0,
    op: 50,
    st: 0,
    bm: 0
  });

  return l;
}

// ── 16. WIZARD STEP ILLUSTRATIONS (6 Steps) ──
function buildWizardStepBadge(label, iconType) {
  const l = baseLottie("Wizard Step " + label, 80, 80, 60, 60);

  l.layers.push({
    ddd: 0,
    ind: 1,
    ty: 4,
    nm: "Step Badge",
    sr: 1,
    ks: {
      o: { a: 0, k: 100 },
      r: { a: 0, k: 0 },
      p: { a: 0, k: [40, 40, 0] },
      a: { a: 0, k: [0, 0, 0] },
      s: {
        a: 1,
        k: [
          { t: 0, s: [40, 40, 100], e: [115, 115, 100], i: { x: [0.2], y: [1] }, o: { x: [0.1], y: [0] } },
          { t: 25, s: [115, 115, 100], e: [100, 100, 100], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 60, s: [100, 100, 100] }
        ]
      }
    },
    ao: 0,
    shapes: [
      {
        ty: "gr",
        it: [
          { ty: "el", d: 1, p: { a: 0, k: [0, 0] }, s: { a: 0, k: [46, 46] }, nm: "Bkg" },
          { ty: "fl", c: { a: 0, k: makeColor("#FFF1F2") }, o: { a: 0, k: 100 }, r: 1, nm: "BkgF" },
          { ty: "st", c: { a: 0, k: makeColor("#E11D48") }, o: { a: 0, k: 100 }, w: { a: 0, k: 3.5 }, lc: 2, lj: 2, nm: "BkgSt" },
          makeTr()
        ],
        nm: "BadgeG"
      }
    ],
    ip: 0,
    op: 60,
    st: 0,
    bm: 0
  });

  return l;
}

// ── Master Catering Loading Screen Animation (NO LOGO, 100% Culinary Life) ──
function buildCateringLoading() {
  const l = baseLottie("Catering Master Loader", 300, 300, 120, 60);

  // 1. Radiant Glowing Aura Base
  l.layers.push({
    ddd: 0, ind: 1, ty: 4, nm: "Aura Ring", sr: 1,
    ks: {
      o: { a: 1, k: [
        { t: 0, s: [30], e: [70], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
        { t: 60, s: [70], e: [30], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
        { t: 120, s: [30] }
      ]},
      r: { a: 0, k: 0 },
      p: { a: 0, k: [150, 190, 0] },
      a: { a: 0, k: [0, 0, 0] },
      s: { a: 1, k: [
        { t: 0, s: [85, 45, 100], e: [110, 55, 100], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
        { t: 60, s: [110, 55, 100], e: [85, 45, 100], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
        { t: 120, s: [85, 45, 100] }
      ]}
    },
    ao: 0,
    shapes: [{
      ty: "gr",
      it: [
        { ty: "el", d: 1, p: { a: 0, k: [0, 0] }, s: { a: 0, k: [180, 70] }, nm: "Oval" },
        { ty: "fl", c: { a: 0, k: makeColor("#E11D48") }, o: { a: 0, k: 40 }, nm: "Fill" },
        { ty: "st", c: { a: 0, k: makeColor("#F59E0B") }, o: { a: 0, k: 70 }, w: { a: 0, k: 3 }, nm: "Stroke" },
        makeTr()
      ],
      nm: "AuraGroup"
    }],
    ip: 0, op: 120, st: 0, bm: 0
  });

  // 2. Rising Swirling Aroma Steam Wisps (4 wisps with lively wavy curves)
  for (let i = 0; i < 4; i++) {
    const xOffset = (i - 1.5) * 28;
    l.layers.push({
      ddd: 0, ind: 2 + i, ty: 4, nm: "Steam " + i, sr: 1,
      ks: {
        o: { a: 1, k: [
          { t: i * 18, s: [0], e: [85], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: i * 18 + 35, s: [85], e: [0], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 120, s: [0] }
        ]},
        r: { a: 0, k: 0 },
        p: { a: 1, k: [
          { t: i * 18, s: [150 + xOffset, 145, 0], e: [150 + xOffset + (i % 2 === 0 ? 12 : -12), 75, 0], i: { x: [0.2], y: [1] }, o: { x: [0.1], y: [0] } },
          { t: i * 18 + 65, s: [150 + xOffset + (i % 2 === 0 ? 12 : -12), 75, 0] }
        ]},
        a: { a: 0, k: [0, 0, 0] },
        s: { a: 1, k: [
          { t: i * 18, s: [60, 60, 100], e: [130, 130, 100], i: { x: [0.2], y: [1] }, o: { x: [0.1], y: [0] } },
          { t: i * 18 + 65, s: [130, 130, 100] }
        ]}
      },
      ao: 0,
      shapes: [{
        ty: "gr",
        it: [
          {
            ty: "sh", d: 1,
            ks: {
              a: 0,
              k: {
                c: false,
                v: [[0, 24], [8, 12], [-6, -6], [2, -24]],
                i: [[0, 0], [-5, 5], [5, 5], [0, 0]],
                o: [[0, 0], [5, -5], [-5, -5], [0, 0]]
              }
            },
            nm: "Path"
          },
          { ty: "st", c: { a: 0, k: makeColor(i % 2 === 0 ? "#F59E0B" : "#FFFFFF") }, o: { a: 0, k: 85 }, w: { a: 0, k: 3.5 }, lc: 2, lj: 2, nm: "Stroke" },
          makeTr()
        ],
        nm: "SteamGroup"
      }],
      ip: 0, op: 120, st: 0, bm: 0
    });
  }

  // 3. Delicious Hot Food on the platter
  l.layers.push({
    ddd: 0, ind: 6, ty: 4, nm: "Gourmet Dish Food", sr: 1,
    ks: {
      o: { a: 0, k: 100 },
      r: { a: 0, k: 0 },
      p: { a: 0, k: [150, 166, 0] },
      a: { a: 0, k: [0, 0, 0] },
      s: { a: 1, k: [
        { t: 0, s: [98, 98, 100], e: [102, 102, 100], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
        { t: 60, s: [102, 102, 100], e: [98, 98, 100], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
        { t: 120, s: [98, 98, 100] }
      ]}
    },
    ao: 0,
    shapes: [
      {
        ty: "gr",
        it: [
          { ty: "el", d: 1, p: { a: 0, k: [0, 0] }, s: { a: 0, k: [76, 26] }, nm: "FoodBase" },
          { ty: "fl", c: { a: 0, k: makeColor("#F59E0B") }, o: { a: 0, k: 95 }, nm: "BaseFill" },
          { ty: "el", d: 1, p: { a: 0, k: [-12, -4] }, s: { a: 0, k: [32, 18] }, nm: "Meat1" },
          { ty: "fl", c: { a: 0, k: makeColor("#B91C1C") }, o: { a: 0, k: 95 }, nm: "Meat1Fill" },
          { ty: "el", d: 1, p: { a: 0, k: [12, -4] }, s: { a: 0, k: [30, 18] }, nm: "Meat2" },
          { ty: "fl", c: { a: 0, k: makeColor("#991B1B") }, o: { a: 0, k: 95 }, nm: "Meat2Fill" },
          { ty: "el", d: 1, p: { a: 0, k: [0, -10] }, s: { a: 0, k: [10, 10] }, nm: "Herb1" },
          { ty: "fl", c: { a: 0, k: makeColor("#10B981") }, o: { a: 0, k: 100 }, nm: "Herb1Fill" },
          { ty: "el", d: 1, p: { a: 0, k: [-6, -8] }, s: { a: 0, k: [7, 7] }, nm: "Herb2" },
          { ty: "fl", c: { a: 0, k: makeColor("#34D399") }, o: { a: 0, k: 100 }, nm: "Herb2Fill" },
          makeTr()
        ],
        nm: "FoodGroup"
      }
    ],
    ip: 0, op: 120, st: 0, bm: 0
  });

  // 4. Cloche Dome (Lifting, tilting playfully)
  l.layers.push({
    ddd: 0, ind: 7, ty: 4, nm: "Cloche Dome Lifting", sr: 1,
    ks: {
      o: { a: 0, k: 100 },
      r: { a: 1, k: [
        { t: 0, s: [0], e: [-7], i: { x: [0.3], y: [1] }, o: { x: [0.1], y: [0] } },
        { t: 40, s: [-7], e: [5], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
        { t: 75, s: [5], e: [0], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
        { t: 120, s: [0] }
      ]},
      p: { a: 1, k: [
        { t: 0, s: [150, 165, 0], e: [150, 122, 0], i: { x: [0.2], y: [1] }, o: { x: [0.1], y: [0] } },
        { t: 45, s: [150, 122, 0], e: [150, 130, 0], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
        { t: 80, s: [150, 130, 0], e: [150, 165, 0], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
        { t: 120, s: [150, 165, 0] }
      ]},
      a: { a: 0, k: [0, 0, 0] },
      s: { a: 1, k: [
        { t: 0, s: [100, 100, 100], e: [106, 106, 100], i: { x: [0.2], y: [1] }, o: { x: [0.1], y: [0] } },
        { t: 45, s: [106, 106, 100], e: [100, 100, 100], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
        { t: 120, s: [100, 100, 100] }
      ]}
    },
    ao: 0,
    shapes: [
      {
        ty: "gr",
        it: [
          { ty: "el", d: 1, p: { a: 0, k: [0, -56] }, s: { a: 0, k: [18, 18] }, nm: "Knob" },
          { ty: "fl", c: { a: 0, k: makeColor("#F59E0B") }, o: { a: 0, k: 100 }, nm: "KnobFill" },
          { ty: "st", c: { a: 0, k: makeColor("#FFFFFF") }, o: { a: 0, k: 80 }, w: { a: 0, k: 2.5 }, nm: "KnobStroke" },
          {
            ty: "sh", d: 1,
            ks: {
              a: 0,
              k: {
                c: true,
                v: [[-62, 0], [62, 0], [60, -6], [0, -50], [-60, -6]],
                i: [[0, 0], [0, 0], [0, 0], [38, 0], [0, -26]],
                o: [[0, 0], [0, 0], [0, -26], [-38, 0], [0, 0]]
              }
            },
            nm: "DomePath"
          },
          { ty: "fl", c: { a: 0, k: makeColor("#E11D48") }, o: { a: 0, k: 95 }, nm: "DomeFill" },
          { ty: "st", c: { a: 0, k: makeColor("#FFFFFF") }, o: { a: 0, k: 90 }, w: { a: 0, k: 4 }, lc: 2, lj: 2, nm: "DomeStroke" },
          {
            ty: "sh", d: 1,
            ks: {
              a: 0,
              k: {
                c: false,
                v: [[-56, -3], [0, -20], [56, -3]],
                i: [[0, 0], [-25, 0], [0, 0]],
                o: [[0, 0], [25, 0], [0, 0]]
              }
            },
            nm: "AccentRibbon"
          },
          { ty: "st", c: { a: 0, k: makeColor("#F59E0B") }, o: { a: 0, k: 100 }, w: { a: 0, k: 3.5 }, lc: 2, lj: 2, nm: "RibbonStroke" },
          makeTr()
        ],
        nm: "ClocheGroup"
      }
    ],
    ip: 0, op: 120, st: 0, bm: 0
  });

  // 5. Silver Platter Base Tray
  l.layers.push({
    ddd: 0, ind: 8, ty: 4, nm: "Silver Platter Tray", sr: 1,
    ks: {
      o: { a: 0, k: 100 },
      r: { a: 0, k: 0 },
      p: { a: 0, k: [150, 176, 0] },
      a: { a: 0, k: [0, 0, 0] },
      s: { a: 1, k: [
        { t: 0, s: [100, 100, 100], e: [103, 103, 100], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
        { t: 60, s: [103, 103, 100], e: [100, 100, 100], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
        { t: 120, s: [100, 100, 100] }
      ]}
    },
    ao: 0,
    shapes: [
      {
        ty: "gr",
        it: [
          { ty: "rc", d: 1, p: { a: 0, k: [0, 0] }, s: { a: 0, k: [154, 12] }, r: { a: 0, k: 6 }, nm: "TrayRim" },
          { ty: "fl", c: { a: 0, k: makeColor("#F3F4F6") }, o: { a: 0, k: 100 }, nm: "TrayFill" },
          { ty: "st", c: { a: 0, k: makeColor("#F59E0B") }, o: { a: 0, k: 100 }, w: { a: 0, k: 3 }, lc: 2, lj: 2, nm: "TrayGoldTrim" },
          { ty: "rc", d: 1, p: { a: 0, k: [0, 7] }, s: { a: 0, k: [120, 6] }, r: { a: 0, k: 3 }, nm: "LowerLip" },
          { ty: "fl", c: { a: 0, k: makeColor("#9CA3AF") }, o: { a: 0, k: 80 }, nm: "LipFill" },
          makeTr()
        ],
        nm: "TrayGroup"
      }
    ],
    ip: 0, op: 120, st: 0, bm: 0
  });

  // 6. Dancing Utensils
  // Fork
  l.layers.push({
    ddd: 0, ind: 9, ty: 4, nm: "Dancing Fork", sr: 1,
    ks: {
      o: { a: 0, k: 90 },
      r: { a: 1, k: [
        { t: 0, s: [-15], e: [-28], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
        { t: 60, s: [-28], e: [-15], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
        { t: 120, s: [-15] }
      ]},
      p: { a: 1, k: [
        { t: 0, s: [52, 160, 0], e: [50, 148, 0], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
        { t: 60, s: [50, 148, 0], e: [52, 160, 0], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
        { t: 120, s: [52, 160, 0] }
      ]},
      a: { a: 0, k: [0, 0, 0] },
      s: { a: 0, k: [95, 95, 100] }
    },
    ao: 0,
    shapes: [
      {
        ty: "gr",
        it: [
          { ty: "rc", d: 1, p: { a: 0, k: [0, 15] }, s: { a: 0, k: [5, 45] }, r: { a: 0, k: 2 }, nm: "FHandle" },
          { ty: "fl", c: { a: 0, k: makeColor("#E5E7EB") }, o: { a: 0, k: 100 }, nm: "FFill" },
          { ty: "rc", d: 1, p: { a: 0, k: [0, -18] }, s: { a: 0, k: [14, 22] }, r: { a: 0, k: 3 }, nm: "FTines" },
          { ty: "fl", c: { a: 0, k: makeColor("#F59E0B") }, o: { a: 0, k: 100 }, nm: "TinesFill" },
          makeTr()
        ],
        nm: "ForkGroup"
      }
    ],
    ip: 0, op: 120, st: 0, bm: 0
  });

  // Spoon
  l.layers.push({
    ddd: 0, ind: 10, ty: 4, nm: "Dancing Spoon", sr: 1,
    ks: {
      o: { a: 0, k: 90 },
      r: { a: 1, k: [
        { t: 0, s: [15], e: [28], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
        { t: 60, s: [28], e: [15], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
        { t: 120, s: [15] }
      ]},
      p: { a: 1, k: [
        { t: 0, s: [248, 160, 0], e: [250, 148, 0], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
        { t: 60, s: [250, 148, 0], e: [248, 160, 0], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
        { t: 120, s: [248, 160, 0] }
      ]},
      a: { a: 0, k: [0, 0, 0] },
      s: { a: 0, k: [95, 95, 100] }
    },
    ao: 0,
    shapes: [
      {
        ty: "gr",
        it: [
          { ty: "rc", d: 1, p: { a: 0, k: [0, 15] }, s: { a: 0, k: [5, 45] }, r: { a: 0, k: 2 }, nm: "SHandle" },
          { ty: "fl", c: { a: 0, k: makeColor("#E5E7EB") }, o: { a: 0, k: 100 }, nm: "SFill" },
          { ty: "el", d: 1, p: { a: 0, k: [0, -18] }, s: { a: 0, k: [16, 24] }, nm: "SBowl" },
          { ty: "fl", c: { a: 0, k: makeColor("#F59E0B") }, o: { a: 0, k: 100 }, nm: "BowlFill" },
          makeTr()
        ],
        nm: "SpoonGroup"
      }
    ],
    ip: 0, op: 120, st: 0, bm: 0
  });

  // 7. Sparkle Stars
  const sparkles = [[80, 105], [220, 100], [150, 52], [105, 65], [195, 68]];
  sparkles.forEach((pos, idx) => {
    l.layers.push({
      ddd: 0, ind: 11 + idx, ty: 4, nm: "Sparkle " + idx, sr: 1,
      ks: {
        o: { a: 1, k: [
          { t: idx * 16, s: [0], e: [100], i: { x: [0.2], y: [1] }, o: { x: [0.1], y: [0] } },
          { t: idx * 16 + 25, s: [100], e: [0], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 120, s: [0] }
        ]},
        r: { a: 1, k: [
          { t: idx * 16, s: [0], e: [90], i: { x: [0.2], y: [1] }, o: { x: [0.1], y: [0] } },
          { t: 120, s: [90] }
        ]},
        p: { a: 0, k: [pos[0], pos[1], 0] },
        a: { a: 0, k: [0, 0, 0] },
        s: { a: 1, k: [
          { t: idx * 16, s: [20, 20, 100], e: [110, 110, 100], i: { x: [0.2], y: [1] }, o: { x: [0.1], y: [0] } },
          { t: idx * 16 + 25, s: [110, 110, 100], e: [0, 0, 100], i: { x: [0.4], y: [1] }, o: { x: [0.2], y: [0] } },
          { t: 120, s: [0, 0, 100] }
        ]}
      },
      ao: 0,
      shapes: [{
        ty: "gr",
        it: [
          {
            ty: "sh", d: 1,
            ks: {
              a: 0,
              k: {
                c: true,
                v: [[0, -9], [3, -3], [9, 0], [3, 3], [0, 9], [-3, 3], [-9, 0], [-3, -3]],
                i: [[0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0]],
                o: [[0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0]]
              }
            },
            nm: "StarPath"
          },
          { ty: "fl", c: { a: 0, k: makeColor("#F59E0B") }, o: { a: 0, k: 100 }, nm: "StarFill" },
          makeTr()
        ],
        nm: "StarGroup"
      }],
      ip: 0, op: 120, st: 0, bm: 0
    });
  });

  return l;
}

// Generate files map
const files = {
  "catering-loading.json": buildCateringLoading(),
  "logo-splash.json": buildLogoSplash(),
  "cloche-idle.json": buildClocheIdle(),
  "icon-package.json": buildIconPackage(),
  "icon-calendar.json": buildIconCalendar(),
  "icon-utensils.json": buildIconUtensils(),
  "icon-filetext.json": buildIconFileText(),
  "icon-shield-check.json": buildIconShieldCheck(),
  "icon-users.json": buildIconUsers(),
  "icon-lock.json": buildIconLock(),
  "icon-theme-toggle.json": buildIconThemeToggle(),
  "icon-fullscreen.json": buildIconFullscreen(),
  "icon-settings-gear.json": buildIconSettingsGear(),
  "empty-plate.json": buildEmptyPlate(),
  "toast-success.json": buildToastSuccess(),
  "toast-info.json": buildToastInfo(),
  "step-customer.json": buildWizardStepBadge("Customer", "user"),
  "step-event.json": buildWizardStepBadge("Event", "calendar"),
  "step-menu.json": buildWizardStepBadge("Menu", "utensils"),
  "step-addons.json": buildWizardStepBadge("Add-ons", "package"),
  "step-billing.json": buildWizardStepBadge("Billing", "credit-card"),
  "step-confirm.json": buildWizardStepBadge("Confirm", "check")
};

let count = 0;
for (const [filename, content] of Object.entries(files)) {
  const p = path.join(OUT_DIR, filename);
  fs.writeFileSync(p, JSON.stringify(content, null, 2));
  count++;
}

console.log(`Successfully generated ${count} bespoke Lottie animations in ${OUT_DIR}`);
