# 🍀 clover

**The cost-of-living crisis, in your community's mental health.**

A data tool that maps how economic stressors flow through to regional mental health pressure - the same way [Tare](https://github.com/prismatic-labs/tare) maps supply chain disruptions to food prices.

→ **[See the tool](https://prismatic-labs.github.io/clover/)**

---

## What is this?

Housing costs have surged. Interest rates nearly doubled. Real wages haven't kept pace. These aren't just economic statistics - they're stressors with well-documented effects on mental health.

**Clover** quantifies how much systemic economic pressure is bearing on mental health in a given region - across 5 stressors and 10 countries. Every weight and transmission pathway is grounded in published epidemiological evidence.

---

## How it works

Each stressor is scored by its **pressure index** - a composite measure of how much current economic conditions have deteriorated relative to a pre-pandemic (2019-2020) baseline, weighted by the published evidence for that stressor's mental health impact.

**Severity bands:**
| Band | Range | Meaning |
|------|-------|---------|
| Extreme | 60-100% | Severe systemic pressure on regional mental health |
| High | 40-59% | Significant stressor exposure |
| Moderate | 20-39% | Measurable but partial pressure |
| Low | 0-19% | Largely insulated |

Regional multipliers adjust for each country's safety net strength, mental health infrastructure, and healthcare access. The same stressor hits harder in countries without universal healthcare or with weak social insurance.

Data updates weekly via GitHub Actions.

---

## Stressors (Phase 1: Economic)

| Stressor | Key indicators | Evidence base | Effect size |
|----------|---------------|---------------|-------------|
| 🏠 Housing Cost Burden | Rent-to-income, mortgage rates, supply gap | Bentley et al., 2011 | OR 1.3-1.5 |
| 📉 Unemployment | U-3, long-term, underemployment (U-6) | Paul & Moser, 2009 | d=0.51 |
| 🔥 Inflation Pressure | CPI food+energy, real wage growth, sentiment | Rohde et al., 2016 | OR 1.1-1.3 |
| 💳 Consumer Debt | Debt-to-income, delinquency, insolvency | Sweet et al., 2013 | OR 1.2-1.4 |
| ⚖️ Income Inequality | Gini, median-mean wage ratio, top 10% share | Pickett & Wilkinson, 2015 | r=0.47 |

---

## Evidence base

All transmission weights are grounded in published, peer-reviewed research:

- **Paul, K.I. & Moser, K. (2009).** Unemployment impairs mental health: Meta-analyses. *Journal of Vocational Behavior*, 74(3), 264-282. 237 cross-sectional and 87 longitudinal studies.
- **Bentley, R. et al. (2011).** Association between housing affordability and mental health: A longitudinal analysis. *Social Science & Medicine*, 73(12), 1771-1780.
- **Rohde, N. et al. (2016).** The effect of economic insecurity on mental health: Recent evidence from Australian panel data. *Social Science & Medicine*, 151, 250-258.
- **Sweet, E. et al. (2013).** The high price of debt: Household financial debt and its impact on mental and physical health. *Social Science & Medicine*, 91, 94-100.
- **Richardson, T. et al. (2013).** The relationship between personal unsecured debt and mental and physical health: A systematic review and meta-analysis. *Clinical Psychology Review*, 33(8), 1148-1162.
- **Pickett, K.E. & Wilkinson, R.G. (2015).** Income inequality and health: A causal review. *Social Science & Medicine*, 128, 316-326.
- **Frasquilho, D. et al. (2016).** Mental health outcomes in times of economic recession: A systematic literature review. *BMC Public Health*, 16, 115.
- **WHO (2014).** Social Determinants of Mental Health. World Health Organization & Calouste Gulbenkian Foundation.
- **Patel, V. et al. (2018).** The Lancet Commission on global mental health and sustainable development. *The Lancet*, 392(10157), 1553-1598.

---

## What Clover is NOT

- **Not a diagnostic tool.** Clover measures systemic stressor pressure, not individual mental health.
- **Not a substitute for professional care.** If you or someone you know is struggling, contact a helpline.
- **Not claiming complete attribution.** Individual, genetic, and biographical factors are real and significant. Clover measures the systemic component only.

**Crisis resources:**
- 🇺🇸 988 Suicide & Crisis Lifeline: call or text **988**
- 💬 Crisis Text Line: text **HOME** to **741741**
- 🌍 International: [findahelpline.com](https://findahelpline.com)

---

## Regional multipliers

Each country has an **impact multiplier** based on structural factors that buffer or amplify economic shocks:

| Factor | What it captures |
|--------|-----------------|
| Safety net strength | Unemployment benefits, welfare access (OECD Social Expenditure DB) |
| Mental health infrastructure | Therapists per 100k population (WHO Mental Health Atlas) |
| Universal healthcare | Whether mental health is covered without cost barrier (WHO NHA) |
| Income inequality (Gini) | How unevenly economic shocks distribute (World Bank) |

A 2% rise in unemployment means something very different in Sweden (strong safety net, universal healthcare, multiplier ~0.6x) vs. the US (employer-linked insurance, weak safety net, multiplier ~1.2x).

---

## Data sources

All free, all open:

| Source | What it provides |
|--------|-----------------|
| [FRED (Federal Reserve)](https://fred.stlouisfed.org/) | Unemployment, CPI, mortgage rates, consumer sentiment, delinquency rates |
| [BLS (Bureau of Labor Statistics)](https://www.bls.gov/) | Employment stats, wage data, CPI components |
| [OECD](https://data.oecd.org/) | Cross-country economic indicators, social expenditure, Better Life Index |
| [Eurostat](https://ec.europa.eu/eurostat) | EU employment, housing costs, income inequality |
| [Zillow ZHVI](https://www.zillow.com/research/data/) | US housing price indices |
| [World Bank](https://data.worldbank.org/) | Gini coefficients, development indicators |
| [WHO Mental Health Atlas](https://www.who.int/publications/i/item/9789240036703) | Mental health workforce and service availability by country |

---

## Run locally

Just open `index.html` in a browser - no server required.

To update the data:

```bash
pip install requests
export FRED_API_KEY=your_key_here  # Free from https://fred.stlouisfed.org/docs/api/api_key.html
python3 scripts/fetch-data.py
```

The script is idempotent and fails gracefully: if any data source is unavailable, it keeps the previous values and continues.

---

## Embeddable widget

```html
<div data-clover-stressor="housing_cost_burden" data-clover-country="US"></div>
<div data-clover-stressor="unemployment" data-clover-country="GB"></div>
<script src="https://prismatic-labs.github.io/clover/widget.js" async></script>
```

Supports `data-clover-theme="dark"` for dark backgrounds. Crisis resources link is always included in the widget.

---

## Roadmap

- **Phase 1 (now):** Economic stressors - housing, unemployment, inflation, debt, inequality. 10 countries.
- **Phase 2:** Environmental stressors - air quality (PM2.5), extreme weather, green space access, urban heat.
- **Phase 3:** Social stressors - social isolation indices, digital overload indicators.

---

## Why "clover"?

In ecology, clover (*Trifolium*) is a **bioindicator** - its presence or absence tells you about the health of the soil. It's in the same plant family as [vetch](https://github.com/prismatic-labs/vetch) and [tare](https://github.com/prismatic-labs/tare).

Vetch fixes nitrogen in the soil. Tare grows among the wheat, revealing what's hidden. Clover tells you what condition the soil is in.

Same family, different job.

---

## Part of Prismatic Labs

Clover is built by [Prismatic Labs](https://prismaticlabs.ai). We build the sensing layer for planet-aware AI - measuring what systems depend on, from GPU tokens to grocery prices to community wellbeing.

---

## License

Apache 2.0
