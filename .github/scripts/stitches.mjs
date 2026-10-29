// Draws the last year of contributions as cross-stitch on linen, one X per day.
// node .github/scripts/stitches.mjs <github-user> <out-dir>   (needs GITHUB_TOKEN)

import { readFileSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const [user = "lzbedat3", outDir = "dist"] = process.argv.slice(2);

const THEMES = {
  dark: {
    bg: "#2A0D1E", ink: "#FFEAF3", mute: "#C690AB", hole: "#FFEAF3", holeOp: 0.13, linen: 0.045,
    shadow: "#12030B", shadowOp: 0.55, thread: ["#7E2A57", "#C8237E", "#FF3FA4", "#FF9BCD"], spine: "#FF3FA4",
  },
  light: {
    bg: "#FFF5F9", ink: "#3A0B24", mute: "#87536E", hole: "#3A0B24", holeOp: 0.12, linen: 0.06,
    shadow: "#7A1747", shadowOp: 0.2, thread: ["#F7B3D2", "#F0559F", "#E0137F", "#A50D5C"], spine: "#E0137F",
  },
};

async function contributions() {
  const query = `query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
    totalContributions weeks{contributionDays{date contributionCount contributionLevel}}}}}}`;
  const res = await fetch("https://api.github.com/graphql", {
    method: "POST",
    headers: { Authorization: `bearer ${process.env.GITHUB_TOKEN}`, "Content-Type": "application/json" },
    body: JSON.stringify({ query, variables: { login: user } }),
  });
  const json = await res.json();
  if (!res.ok || json.errors) throw new Error(JSON.stringify(json.errors ?? json));
  return json.data.user.contributionsCollection.contributionCalendar;
}

const LEVEL = { NONE: -1, FIRST_QUARTILE: 0, SECOND_QUARTILE: 1, THIRD_QUARTILE: 2, FOURTH_QUARTILE: 3 };

function render(cal, t) {
  const font = readFileSync(join(here, "ubuntu-500.b64"), "utf8").trim();
  const W = 1200, cell = 17, cols = cal.weeks.length;
  const gx = Math.round((W - cols * cell) / 2), gy = 150, H = gy + 7 * cell + 90;
  const days = cal.weeks.flatMap((w) => w.contributionDays).filter((d) => d.contributionCount > 0).length;

  let holes = "", stitches = "";
  cal.weeks.forEach((week, col) => {
    week.contributionDays.forEach((day) => {
      const row = new Date(day.date + "T00:00:00Z").getUTCDay();
      const x = gx + col * cell, y = gy + row * cell;
      const lvl = LEVEL[day.contributionLevel] ?? -1;
      if (lvl < 0) {
        holes += `<circle cx="${x + cell / 2}" cy="${y + cell / 2}" r="1.3"/>`;
        return;
      }
      const c = t.thread[lvl], p = 3.4, a = x + p, b = x + cell - p, u = y + p, v = y + cell - p;
      stitches +=
        `<g style="animation-delay:${(0.3 + col * 0.035).toFixed(2)}s" class="x">` +
        `<path d="M${a} ${u}L${b} ${v}M${b} ${u}L${a} ${v}" stroke="${t.shadow}" stroke-opacity="${t.shadowOp}" transform="translate(.8 1.1)"/>` +
        `<path d="M${a} ${u}L${b} ${v}" stroke="${c}"/><path d="M${b} ${u}L${a} ${v}" stroke="${c}" stroke-opacity=".92"/>` +
        `<path d="M${b - 1} ${u + 1}L${a + 2.6} ${v - 2.6}" stroke="#fff" stroke-opacity=".3" stroke-width="1"/></g>`;
    });
  });

  const total = cal.totalContributions;
  const title = "My year on GitHub, cross-stitched";
  const note = `${total} contributions over ${days} days. Darker thread means a busier day.`;
  const fx = gx - 22, fw = cols * cell + 44, fy = gy - 22, fh = 7 * cell + 44;

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-labelledby="t d">
<title id="t">${title}</title><desc id="d">${note}</desc>
<style>@font-face{font-family:U;font-weight:500;src:url(data:font/woff2;base64,${font}) format('woff2')}
text{font-family:U,Ubuntu,sans-serif}
.x{opacity:0;animation:x .35s ease-out forwards}.x path{fill:none;stroke-width:2.6;stroke-linecap:round}
@keyframes x{from{opacity:0;transform:translateY(-3px)}to{opacity:1;transform:none}}
.draw{stroke-dasharray:1 1;stroke-dashoffset:1;animation:draw 1.6s cubic-bezier(.65,0,.35,1) .1s forwards}
@keyframes draw{to{stroke-dashoffset:0}}
@media (prefers-reduced-motion:reduce){.x{animation:none;opacity:1}.draw{animation:none;stroke-dashoffset:0}}</style>
<defs><pattern id="linen" width="6" height="6" patternUnits="userSpaceOnUse">
<path d="M0 1.5H6M0 4.5H6M1.5 0V6M4.5 0V6" stroke="${t.ink}" stroke-opacity="${t.linen}" stroke-width=".8"/></pattern>
<mask id="sm" maskUnits="userSpaceOnUse"><path d="M1140 0V${H}" stroke="#fff" stroke-width="14" pathLength="1" class="draw"/></mask></defs>
<rect width="${W}" height="${H}" fill="${t.bg}"/><rect width="${W}" height="${H}" fill="url(#linen)"/>
<g mask="url(#sm)"><path d="M1140 0C1154 ${H * 0.4} 1126 ${H * 0.7} 1140 ${H}" fill="none" stroke="${t.spine}" stroke-width="3.2" stroke-dasharray="15 10" stroke-linecap="round"/></g>
<text x="80" y="66" font-size="30" font-weight="500" fill="${t.ink}">${title}</text>
<text x="80" y="102" font-size="18" font-weight="500" fill="${t.mute}">${note}</text>
<rect x="${fx}" y="${fy}" width="${fw}" height="${fh}" rx="10" fill="none" stroke="${t.hole}" stroke-opacity="${t.holeOp * 1.4}" stroke-width="1.4" stroke-dasharray="6 5"/>
<g fill="${t.hole}" fill-opacity="${t.holeOp}">${holes}</g>
${stitches}
</svg>
`;
}

const cal = await contributions();
mkdirSync(outDir, { recursive: true });
for (const [name, theme] of Object.entries(THEMES)) {
  writeFileSync(join(outDir, `stitches-${name}.svg`), render(cal, theme));
}
console.log(`stitched ${cal.totalContributions} contributions for ${user}`);
