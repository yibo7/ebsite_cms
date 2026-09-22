"""
批量发布测试 - 7 篇中喷网文章英文版

自动生成，通过 HMAC 签名 API 发布到 CMS。
"""
import hmac
import hashlib
import time

import requests

CMS_BASE_URL = "http://127.0.0.1:8066"
SITE_KEY = "a0580f89a93b4a8f81c1a0595609a8dd"
USER_ID = 10
CLASS_ID = 106

ARTICLES = [
    # ── 1. Durst P5 350 CORE ──
    {
        "title": "Durst Unveils P5 350 CORE: A Future-Ready Hybrid Printing Platform Built for Mid-Market Growth",
        "content": """In September 2026, Durst Group introduced the P5 350 CORE hybrid digital printing platform, a new system engineered to bridge the gap between conventional analog workflows and high-performance industrial digital printing. Rather than stripping down features to cut costs, Durst built the P5 350 CORE on the same proven technology architecture as its established P5 series, allowing businesses stepping into digital production to immediately benefit from field-validated stability and performance.

The platform is backed by Durst's global service network spanning more than 80 countries, with an average first-response time of just 45 minutes and over 70 percent of issues resolvable remotely. Installed P5-series systems worldwide achieve an average uptime of 96 percent. Built around Durst's XT expansion technology, the P5 350 CORE combines modular hardware with a unified software ecosystem and supports ongoing upgrades. It natively integrates with the Kyveris intelligent software suite via open APIs and sensor-layer data, enabling workflow analysis and process optimization without replacing existing infrastructure.

The system complies with GREENGUARD Gold and REACH environmental standards, and its optimized ink delivery can cut consumption by up to 30 percent. Durst offers tailored financing plans and customized deployment to help businesses transition into digital production. Supporting both rigid board and roll-to-roll configurations, the P5 350 CORE comes in six variants from manual to fully automated, covering a wide range of shop-floor capacities while maintaining Durst's industrial print quality at a more accessible entry point.""",
        "tags": "durst,inkjet,digital printing",
    },
    # ── 2. 3D Printing ──
    {
        "title": "3D Printing at the Crossroads: Proven Strengths and the Hurdles to Mass Adoption",
        "content": """After four decades of evolution since Charles Hull invented stereolithography in 1984, additive manufacturing has crossed the threshold from lab curiosity to industrial-scale production. According to the Wohlers Report 2026, the global additive manufacturing industry reached $24.2 billion in 2025, growing 10.9 percent year over year. China alone accounts for roughly 70 billion yuan, nearly 30 percent of the worldwide total. Printing services now capture 48 percent of revenue, far outpacing equipment sales at 26 percent, confirming that 3D printing is migrating from prototyping to production.

The technology's core strengths are reshaping manufacturing. Tool-less fabrication collapses multi-step processes into single operations, while topology-optimized lightweighting delivers mechanical properties that subtractive methods cannot match. Powder bed fusion pushes material utilization above 95 percent. GE Aviation's LEAP engine fuel nozzle, a single 3D-printed part replacing a 20-component assembly, has surpassed 250,000 units shipped, cutting part count by 95 percent and weight by 25 percent. Yet penetration in aerospace is just 3.8 percent and in automotive only 0.8 percent.

Cost, speed, and standards remain persistent barriers. Industrial SLM systems range from $400,000 to $3.5 million, and titanium powder can cost thousands per kilogram. Metal powder bed fusion prints at only 10-30 cm per hour. Standards and certification lag behind innovation. The path forward lies in systemic optimization: beam-shaping technology boosting scan speed by 30 percent, closed-loop powder recycling achieving over 95 percent reuse, and end-to-end digital twin quality tracking bringing batch consistency closer to conventional standards.""",
        "tags": "3d printing,additive manufacturing,printing technology",
    },
    # ── 3. Konica Minolta Label Printer ──
    {
        "title": "Konica Minolta Unveils Next-Gen Label Printing System at Japan Label Forum 2026",
        "content": """Konica Minolta has announced its participation in the 2026 Japan Label Forum, scheduled for October 14-16, where it will showcase a new lineup of digital label printing solutions designed to help printers overcome industry-wide challenges of rising quality expectations, tighter cost controls, and demands for greater efficiency.

The standout reveal is the AccurioLabel 231, a next-generation digital label printing system making its Japanese debut. Built as an iterative upgrade to Konica Minolta's mid-range digital label portfolio, it delivers comprehensive improvements in performance, image quality, and operational stability. The system is equipped with the proprietary IQ-530 automatic quality optimization unit, which uses intelligent automation to monitor and adjust color accuracy, density, and registration in real time, eliminating variability associated with manual calibration.

The AccurioLabel 231 achieves a full-speed printing rate of 23.4 meters per minute, paired with an ultra-high resolution of 1200x2400 dpi. It requires no complex pre-treatment and supports a wide variety of media types. Beyond the new hardware, Konica Minolta will host dedicated mini-seminars at its booth focusing on quality enhancement, labor cost reduction, workflow digitalization, and precision order management, drawing on real-world case studies to help print businesses sharpen their competitive edge.""",
        "tags": "konica minolta,label printing,digital printing",
    },
    # ── 4. Brother 325% Profit ──
    {
        "title": "Brother Posts Stunning 325% Profit Surge as Consumables Strategy Fuels Record Quarter",
        "content": """Brother Industries delivered a blockbuster earnings report for the first quarter of fiscal 2026, with net profit attributable to parent company shareholders skyrocketing 325.8 percent year over year to 49.9 billion yen. Consolidated sales revenue rose 23.0 percent to 253.3 billion yen, while operating profit climbed 250.1 percent to 54.6 billion yen. All key metrics hit record highs for the quarter ended June 30, 2026.

The Printing and Solutions segment remained the primary growth engine, generating 159.7 billion yen in revenue. Segment profit nearly tripled from 15.2 billion yen a year earlier to 43.4 billion yen. Notably, consumables accounted for 58 percent of total segment sales, underscoring the strength of Brother's razor-and-blades business model. Laser printer sales grew 5 percent while inkjet slipped 4 percent.

Multiple tailwinds amplified the results. The industrial printing business benefited from the consolidation of MUTOH, and a weaker yen provided a powerful currency tailwind for overseas earnings. Buoyed by the stellar quarter, Brother has raised its full-year guidance. Management acknowledged headwinds including rising raw material costs for memory chips and resins, and persistently high logistics expenses. The company is responding with further price adjustments and stricter cost controls. Brother's deep moat in consumables continues to anchor its financial performance regardless of hardware market fluctuations.""",
        "tags": "brother,printing consumables,financial results",
    },
    # ── 5. Eco3 VEXIS RTR5300 ──
    {
        "title": "Eco3 Launches VEXIS RTR5300: A 5.33-Meter Wide-Format UV Printer Built for Practical Production",
        "content": """Eco3, the industry giant rebranded from the former Agfa Graphics Japan, has announced the launch of the VEXIS RTR5300, a new UV roll-to-roll printer targeting the 5-meter wide-format market. The new machine marks a strategic move in the company's product lineup, addressing a gap in a segment long dominated by high-end models focused on maximum speed and top-tier features.

While demand for large-format printing in outdoor advertising, illuminated signage, and fabric displays continues to grow, many production shops find premium machines carry excessive costs and capabilities beyond their daily needs. The VEXIS RTR5300 is positioned not as a downgraded alternative but as a carefully balanced standard model offering the right performance for real-world production environments.

The printer supports a maximum media width of 5.33 meters with an output resolution of 1200 dpi, ensuring crisp image quality at超大 format sizes. Production speed reaches 318 square meters per hour, suitable for batch orders with tight deadlines. In addition to standard CMYK, the machine offers optional light magenta, light cyan, and white ink channels, expanding its application range from high-quality photographic prints to transparent media and backlit signage requiring white ink base layers.

With the VEXIS RTR5300 joining the JETI CONDOR flagship model, Eco3 has built a clear two-tier product matrix for the 5-meter market. This differentiated approach lets customers choose between ultimate performance and balanced cost-efficiency based on their production scale and budget.""",
        "tags": "eco3,wide format,inkjet printing",
    },
    # ── 6. Pantum AI Inkjet ──
    {
        "title": "Pantum Launches AI-Powered Inkjet Printers That Refuse to Clog Even After a Year of Disuse",
        "content": """Chinese printer brand Pantum unveiled its full-scenario smart printing lineup and a new generation of inkjet printers in Beijing on August 26, 2026. The portfolio includes four desktop Smart AI inkjet models alongside portable variants, extending Pantum's AI capabilities from laser to inkjet across the entire product range.

One of the biggest pain points for inkjet users has always been clogged printheads after periods of inactivity. Pantum's new series tackles this with a three-layer defense: a physical moisturizing structure that prevents ink from drying, a high-pressure ink pump that clears deep impurities, and an intelligent self-cleaning system that performs maintenance sprays every 96 hours. According to CEPREI testing, the printers remain free of dried-ink clogs even after 365 days of idling under standard conditions.

The new models are built on Pantum's AI Agent 4.0 architecture, embedding the Xiaoben AI assistant across the printer body, PC, and mobile devices. It connects to major large language models including DeepSeek and Tongyi Qianwen, allowing users to generate content and initiate printing through voice commands. The devices integrate with Tencent WorkBuddy AI and support HarmonyOS, WeChat, and DingTalk. The Pantum ST1 Color AI Learning Printer supports 4800x1200 dpi resolution, delivers 7,500 black-and-white pages and 4,000 color pages. It starts at 777 yuan on JD.com and comes with a three-year warranty.""",
        "tags": "pantum,ai printing,inkjet",
    },
    # ── 7. Epson SC-F20050 ──
    {
        "title": "Epson Unveils SC-F20050: 8-Head 76-Inch Sublimation Printer Reaching 306 m per Hour",
        "content": """On September 3, 2026, Epson Sales Co., Ltd. introduced the SC-F20050, a 76-inch industrial-grade dye-sublimation transfer printer engineered for high-volume production of soft signage, sportswear, and fan merchandise. The machine addresses two fast-growing markets: soft signage facing peak-season batch orders, and sportswear demanding consistent image quality and color reproduction.

At its core are eight PrecisionCore Micro TFP print heads in a four-color configuration, pushing throughput to 306 square meters per hour at 600x600 dpi in single-pass mode. This represents a roughly 190 percent productivity boost over its predecessor, the SC-F11050 launched in May 2024. For production facilities, this means significantly more output during crunch periods without expanding equipment footprint.

Epson has focused on maintaining print quality at higher speeds through a symmetrical left-right print head layout and horizontal alignment ensuring precise droplet placement. This design minimizes dot-position errors and reduces banding and color inconsistencies. The SC-F20050 offers a high-capacity media unit accommodating rolls up to 500mm in outer diameter weighing 300kg, reducing roll changes during long runs.

The launch extends Epson's push into industrial sublimation printing, following previews of multiple new sublimation technologies at FESPA Barcelona in May 2026. Under its ENGINEERED FUTURE 2035 vision, Epson continues leveraging its save-small-precise philosophy to address the textile industry's growing need for higher productivity and reliability.""",
        "tags": "epson,sublimation printing,textile printing",
    },
]


def main():
    for i, art in enumerate(ARTICLES, 1):
        title = art["title"]
        content = art["content"]
        tags = art["tags"]

        body = (
            f"title={requests.utils.quote(title)}"
            f"&info={requests.utils.quote(content)}"
            f"&tagstr={requests.utils.quote(tags)}"
        )

        timestamp = str(int(time.time()))
        message = f"{timestamp}:{body}"
        sign = hmac.new(
            SITE_KEY.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        url = f"{CMS_BASE_URL}/api/auto_post_content/{USER_ID}/{CLASS_ID}"
        headers = {
            "X-Timestamp": timestamp,
            "X-Sign": sign,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        print(f"[{i}/{len(ARTICLES)}] 📤 发布中: {title[:50]}...")
        resp = requests.post(url, headers=headers, data=body, timeout=30)

        try:
            result = resp.json()
        except Exception:
            result = {"raw": resp.text[:200]}

        status = "✅" if result.get("code") == 0 else "❌"
        print(f"  {status} {result.get('msg', result.get('data', 'unknown'))}")
        print()


if __name__ == "__main__":
    main()