import json, math, os, re, sys, time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = Path(os.environ.get("ASO_RAW", ROOT / "data" / "raw"))
VARIANT = "public" if "--public" in sys.argv else "personal"
SITE = Path(os.environ["ASO_OUT"]) if os.environ.get("ASO_OUT") else ROOT / ("public" if VARIANT == "public" else "site")

TOPICS = [
    ("ETH", "Ethics", r"ethic|standards? of (professional )?(conduct|practice)|code of (ethics|conduct)|\bgips\b|professional conduct|material nonpublic|mosaic theory|fair dealing|suitability|misconduct|independence (and|&) objectivity|duties to (clients|employers)|conflicts? of interest|asset manager code|soft dollar|misrepresentation|market manipulation|\bstandard (i|ii|iii|iv|v|vi|vii)\b|standard [1-7]\b|duty of loyalty"),
    ("QM", "Quantitative Methods", r"quant(itative)? method|\bquants?\b|time value of money|\btvm\b|hypothesis|regression|multicollinear|heterosk|autocorrel|serial correl|probabilit|statistic|sampling|central limit|confidence interval|t-test|chi-square|f-test|anova|correlation|monte carlo|simulation|bootstrap|time[- ]series|\barch\b|unit root|cointegrat|machine learning|big data|fintech|money[- ]weighted|time[- ]weighted|holding period return|geometric mean|annuit|perpetuit|distribution|lognormal|z-score|kurtosis|skewness|covariance|logistic|dummy variable|rates? (and|&) returns?|\bp-value|neural network|text analytics|random walk|stationar"),
    ("ECO", "Economics", r"econom|\bgdp\b|inflation|monetary polic|fiscal polic|central bank|interest rate parity|exchange rate|currenc|\bfx\b|forex|purchasing power parity|\bppp\b|balance of payments|international trade|tariff|supply and demand|demand and supply|elasticit|market structure|monopol|oligopol|perfect competition|business cycle|economic growth|solow|convergence|taylor rule|carry trade|mundell|aggregate (demand|supply)|unemployment|capital flows?|geopolit|recession|quantitative easing|the fed\b|federal reserve|yield curve inversion|tariffs"),
    ("FSA", "Financial Statement Analysis", r"financial statement|\bfsa\b|income statement|balance sheet|cash flow statement|statement of cash flows|cash flows? (from|statement)|revenue recognition|inventor(y|ies)|\bfifo\b|\blifo\b|depreciation|amortization|impairment|intangible|goodwill|\bleases?\b|deferred tax|income tax|pension|post-employment|share-based|stock comp|intercorporate|business combination|equity method|consolidat|multinational operation|foreign currency translation|current rate method|temporal method|ratio analysis|financial ratio|dupont|earnings quality|reporting quality|financial reporting|\bifrs\b|\bgaap\b|accrual|diluted eps|long[- ]lived assets|non-current liabilit|long-term liabilit|financial institutions|camels|financial analysis techniques|accounting|working capital ratio|capitaliz(ing|ation) (of )?(costs|interest)|bonds payable"),
    ("CI", "Corporate Issuers", r"corporate issuer|corporate finance|capital budgeting|\bnpv\b|net present value|cost of capital|\bwacc\b|capital structure|modigliani|\bm ?& ?m\b|mm proposition|operating leverage|financial leverage|dividends?\b|share repurchase|buyback|payout polic|corporate governance|\besg\b|stakeholder|mergers?|acquisition|\bm&a\b|restructuring|working capital management|liquidity management|business model|capital allocation|real options|cost of equity|cost of debt|breakeven|corporate structure"),
    ("EQ", "Equity", r"equity valuation|equity investment|equit(y|ies) (market|securit)|stock valuation|valu(e|ing) (a )?(stocks?|compan|business)|dividend discount|\bddm\b|gordon growth|free cash flow|\bfcff\b|\bfcfe\b|residual income|price multiples?|market multiples?|\bp/?e\b|ev/ebitda|enterprise value|industry analysis|company analysis|porter|five forces|market efficiency|efficient market|\bemh\b|security market index|stock index|private company valuation|discounted cash flow|\bdcf\b|h-model|justified p|sustainable growth|sector analysis|valuation|intrinsic value|equity research|stocks?\b|earnings"),
    ("FI", "Fixed Income", r"fixed income|\bbonds?\b|yield curve|duration|convexity|credit spread|\boas\b|z-spread|option-adjusted|credit risk|credit analysis|credit default|securiti[sz]ation|\babs\b|\bmbs\b|mortgage-backed|asset-backed|\bcmo\b|prepayment|term structure|spot rates?|forward rates?|\bytm\b|yield to maturity|embedded option|callable|putable|convertible|interest rate tree|interest rate risk|immunization|coupon|treasur(y|ies)|sovereign debt|money market|\brepo\b|covered bonds?|credit rating|fixed-income|key rate|yield spread"),
    ("DER", "Derivatives", r"derivativ|\boptions?\b|forward contract|forwards?\b|futures|\bswaps?\b|put-call|black-scholes|\bbsm\b|binomial (option|model|tree)|greeks|delta|gamma|vega|theta|covered call|protective put|collar|straddle|strangle|bull spread|bear spread|butterfly|no-arbitrage|arbitrage|\bfra\b|forward rate agreement|cost of carry|\bvix\b|variance swap|credit default swap|\bcds\b|hedg"),
    ("ALT", "Alternative Investments", r"alternative invest|alternatives\b|hedge funds?|private equity|venture capital|real estate|\breits?\b|commodit|infrastructure|digital asset|crypto|bitcoin|blockchain|private (debt|credit)|natural resources|farmland|timberland|fund of funds|carried interest|waterfall|private markets?|buyout|\blbo\b|real assets"),
    ("TA", "Technical Analysis", r"technical analysis|technical analyst|chart(ing)? patterns?|candlestick|\brsi\b|\bmacd\b|bollinger|elliott wave|canslim|market breadth|dow theory|intermarket analysis|support (and|&) resistance|head and shoulders|\bcmt\b"),
    ("INT", "Investor interviews", r"(?!x)x"),
    ("PM", "Portfolio Management", r"portfolio|\bcapm\b|capital market line|security market line|efficient frontier|markowitz|mean-variance|diversification|systematic risk|\bbeta\b|sharpe|treynor|jensen|\balpha\b|information ratio|multifactor|factor (model|investing)|\bapt\b|arbitrage pricing|risk management|\bvar\b|value at risk|behavio(u)?ral|asset allocation|rebalanc|\bips\b|investment policy statement|performance (attribution|evaluation|measurement|appraisal)|benchmark|active (management|return|risk)|fundamental law|trading costs?|trade execution|\betfs?\b|index fund|passive investing|liability[- ]driven|\bldi\b|institutional investor|endowment|sovereign wealth|insurer|overlay|capital market expectations|\bcme\b|risk (and|&) return|investment management|swap overlay|tail risk|stress test|retirement"),
    ("PW", "Private Wealth", r"private wealth|private client|individual investor|high[- ]net[- ]worth|\bhnwi?\b|estate planning|wealth transfer|\btrusts?\b|tax[- ]efficien|taxes and|after-tax|retirement planning|life insurance|family office|human capital|concentrated (position|wealth)|goals-based|wealth management|financial planning|charitable|gifting"),
    ("EXAM", "Exam & Career", r"\bexam\b|\bstudy\b|calculator|ba ?ii|ti-?84|hp ?12c|prep(aration)?\b|first attempt|how i (teach|cleared|passed|studied)|cleared|replace the cfa|future of (the )?cfa|which is right|study (plan|tips|strategy|schedule|guide)|pass rate|results?\b|mock|how (i|to) pass|motivation|journey|worth it|\bvs\.?\b|career|salary|jobs?\b|interview|constructed response|essay|formula sheet|formulas|revision|cheat sheet|last minute|q&a|question bank|practice (questions|problems)|tips|curriculum (changes|update)|registration|charter|day in the life|advice|failed|passed"),
]
TOPIC_RE = [(k, n, re.compile(p, re.I)) for k, n, p in TOPICS]
FA_SUBS = [
    ("VALUE", "Value investing", r"value investing|value investor|benjamin graham|\bgraham\b|margin of safety|intrinsic value|deep value|net[- ]nets?|book value|value traps?|contrarian|mr\.? market|security analysis|intelligent investor|value stocks?|cigar butt|owner earnings|buffett|munger|berkshire|klarman|pabrai|greenblatt|magic formula|undervalued companies|stock market wisdom"),
    ("GROWTH", "Growth investing", r"growth investing|growth investor|growth stocks?|growth compan|growth portfolio|investing in growth|growth at a reasonable price|philip fisher|scuttlebutt|one up on wall street|peter lynch|\bpeg\b|ten-?baggers?|100-?baggers?|compounders?|compounding machines?|quality (investing|stocks|companies|growth)|total addressable market|\btam\b|high[- ]growth|rule of 40|saas metrics|unit economics|disruptive innovation|founder[- ]led|small caps? growth|garp"),
    ("VAL", "Valuation", r"valuation|valuing|value a (stock|company|business)|\bdcf\b|discounted cash flow|free cash flow|\bfcf\b|multiples|ev/ebitda|enterprise value|\bp/?e ratio|price[- ]to[- ](earnings|book|sales)|cost of capital|\bwacc\b|terminal value|reverse dcf|sum of the parts|damodaran|financial model(l)?ing|\blbo\b|comparable compan|precedent transactions|equity research"),
    ("FS", "Financial statements", r"financial statements?|income statement|balance sheet|cash flow statement|statement of cash flows|\b10-?k\b|\b10-?q\b|annual report|accounting|ratio analysis|financial ratios|earnings quality|quality of earnings|forensic|accounting red flags|\bgaap\b|\bifrs\b|return on (equity|invested capital|capital|assets)|\broic\b|\broce\b|\broe\b|gross margin|operating margin|working capital|depreciation|amortization|ebitda|how to read (a |an )?(10-k|annual report|balance sheet|income statement|financial statements)|debits? (and|&) credits?|revenue recognition"),
    ("ECON", "Economics & macro", r"econom|macro|inflation|interest rates?|the fed\b|federal reserve|central bank|recession|business cycle|\bgdp\b|monetary polic|fiscal polic|debt cycle|yield curve|currenc|exchange rate|bond market|liquidity|unemployment|deflation|stagflation|trade (war|deficit)|tariffs?|supply and demand|elasticity|keynes|hayek|money supply|quantitative easing|productivity"),
    ("COMP", "Industry & competition", r"porter|five forces|competitive (advantage|strategy|position|dynamics|edge)|economic moats?|\bmoats?\b|industry analysis|industry structure|business models?|network effects?|switching costs|pricing power|barriers to entry|value chain|disruption|market share|differentiation|cost leadership|blue ocean|platform business|competitive landscape|(business|corporate|competitive) strategy|strategy of (amazon|apple|costco|walmart|netflix|google|microsoft)"),
    ("PORT", "Portfolio & risk", r"portfolio|asset allocation|diversification|risk management|position sizing|behavio(u)?ral|biases|index funds?|passive investing|factor investing|rebalanc|sharpe|drawdowns?|kelly criterion|modern portfolio theory|efficient frontier|risk (and|&) return|volatility|hedging|options strategy|bonds? vs\.? stocks|retirement|dollar cost averaging"),
    ("INT", "Investor interviews", r"(?!x)x"),
]
FA_RE = [(k, re.compile(p, re.I)) for k, _, p in FA_SUBS]
FA_IDX = {k: i + 1 for i, (k, _, _) in enumerate(FA_SUBS)}
FA_PRIORITY = ["COMP", "FS", "VAL", "VALUE", "GROWTH", "ECON", "PORT"]
TP_TO_FA = {"FSA": "FS", "ECO": "ECON", "PM": "PORT", "PW": "PORT"}
FA_NOISE = re.compile(r"managerial accounting|cost accounting|costs? of quality|process costing|job[- ]order costing|budget(ing|s)?\b|\btax(es|ation)?\b|\birs\b|s corporation|partnership basis|audit(ing|or)?\b|cpa exam|journal entr|payroll|bookkeeping|nonprofit|governmental accounting|accounting major|excel (tips|tutorial|shortcuts)", re.I)
FA_PICK = re.compile(r"is \w+ (stock )?a (buy|sell)|stocks? (to|i'?m) buy|buy (now|or sell)|undervalued stocks? (to|for)|my (portfolio|dividend portfolio|stock portfolio)|portfolio update|i (just )?(bought|sold)|i'?m (buying|selling)|top \d+ stocks|\bearnings (reaction|recap|call)\b|\$[A-Z]{1,5}\b|stock analysis:|price target|#shorts|live ?stream|\blive\b|stocks? (crash|soar|plunge|surge)|this week in|news roundup|market update|\b\d+\s+[\w\- ]{0,30}?(stocks|funds|etfs|picks|reits)\b|to consider|worth a look|is cheap|still compelling|on sale|bargains?\b|buy and hold\b|best (stocks|funds|etfs)|dividend stocks|stock picks?|fund picks", re.I)


def fa_of(text, pl_text):
    sc = {k: 2 * len(rx.findall(text)) + len(rx.findall(pl_text)) for k, rx in FA_RE}
    best = max(FA_PRIORITY, key=lambda k: (sc[k], -FA_PRIORITY.index(k)))
    return FA_IDX[best] if sc[best] else 0
TA_SUBS = [
    ("CANSLIM", "CANSLIM & growth stocks", r"canslim|can slim|o'?neil|cup (with|and|w/) ?handle|follow[- ]through day|distribution days?|\bftd\b|leaderboard|ibd 50|\brs rating|composite rating|minervini|\bvcp\b|volatility contraction|\bsepa\b|trend template|stage (analysis|[1-4])\b|weinstein|super ?performance|growth stocks?|base (count|pattern|breakout)|flat base|pivot (point|buy)|buy points?|market ?school|marketsmith|leadership stocks?|power play|high tight flag|market leaders"),
    ("CYC", "Cycles", r"cycles?\b|hurst|seasonal|presidential (cycle|election)|election year|midterm|decennial|elliott wave|kondratie|kitchin|juglar|\bgann\b|market timing|santa claus rally|sell in may|benner"),
    ("MOM", "Momentum trading", r"momentum|breakouts?|episodic pivots?|relative strength|\brs line|trend[- ]follow|swing trad|position trad|qullamaggie|kullam|anticipation setup|moving averages?|\b(10|20|21|50|200)[- ]?(day|dma|ema|sma)\b|parabolic|gap ?(up|ups|and go)|leading stocks|top gainers|\badr\b|pullbacks?|dual momentum|sector rotation|setups?\b"),
    ("BRD", "Market breadth", r"breadth|advance[- /]decline|a/?d line|mcclellan|summation index|new highs?[ -]*(vs\.?|versus|and|minus|/|-)[ -]*new lows?|net new highs|new 52[- ]week (highs?|lows?) list|high[- ]low (index|indicator)|percent(age)? of stocks|% of stocks|stocks above|bullish percent|\bbpi\b|zweig|\btrin\b|arms index|\$tick\b|up ?volume|market internals|participation|hindenburg|market monitor|t2108|equal[- ]weight"),
    ("TAG", "Charting & indicators", r"technical analysis|chart(ing)? patterns?|candlesticks?|support (and|&) resistance|trend ?lines?|\brsi\b|\bmacd\b|stochastic|bollinger|fibonacci|volume profile|head and shoulders|double (top|bottom)|triangles?|wedges?|\bflags?\b|indicators?|price action|chart(ing)? (school|reading|basics|course|tutorial|lesson)|how to (read|use) (a |stock )?charts?|dow theory|intermarket|cmt (exam|level|program|curriculum)|relative rotation|\brrg\b|point (and|&) figure|ichimoku|vwap|sentiment"),
]
TA_PRIORITY = ["CANSLIM", "BRD", "CYC", "MOM", "TAG"]
TA_DAILY_DROP = ("TAG", "MOM", "CANSLIM")
if VARIANT == "public":
    _p = {k: p for k, _, p in TA_SUBS}
    TA_SUBS = [
        ("CANSLIM", "CANSLIM & growth stocks", _p["CANSLIM"]),
        ("CLASSIC", "Classical chart patterns", r"chart patterns?|classical (chart|charting|technical)|head (and|&) shoulders|double (top|bottom)s?|triple (top|bottom)|triangles?|wedges?|\bflags?\b|pennants?|rectangles?|rounding (top|bottom)|cup and handle|support (and|&) resistance|\bsupport\b|\bresistance\b|trend ?lines?|trend channels?|dow theory|edwards (and|&) magee|peter brandt|price action|gaps? (theory|fill|types)|technical analysis (basics|course|101|for beginners|explained|tutorial|masterclass)|how to (read|use) (a |stock )?charts?|chart(ing)? (school|reading|basics|course|tutorial|lesson)"),
        ("EW", "Elliott Wave", r"elliott|elliot wave|wave count|impulse wave|impulsive|corrective (wave|structure|pattern)|zig ?zag|flat correction|expanded flat|ending diagonal|leading diagonal|\bwave (i{1,3}|iv|v|[1-5]|[abcxyz])\b|\babc\b|wxy|prechter|socionomic|\bewi\b|wave principle|wave theory"),
        ("WYK", "Wyckoff & VSA", r"wyckoff|re-?accumulation|re-?distribution|accumulation (phase|schematic|range|structure)|distribution (phase|schematic|range|structure)|\bspring\b|upthrust|\butad\b|sign of (strength|weakness)|last point of support|\blps\b|composite (man|operator)|volume spread|\bvsa\b|tom williams|no demand|no supply|stopping volume|selling climax|buying climax|effort (vs\.?|versus|and|&) result|smart money|tradeguider|supply (and|&) demand|volume analysis|cause (and|&) effect|bag holding|test (bar|of supply)"),
        ("CANDLE", "Japanese candlesticks", r"candlesticks?|candle ?patterns?|\bdoji\b|\bhammers?\b|engulfing|harami|shooting star|morning star|evening star|marubozu|nison|heikin[- ]?ashi|three white soldiers|three black crows|dark cloud|piercing (line|pattern)|tweezer|hanging man|inside bar|pin ?bar"),
        ("MOM", "Momentum trading", _p["MOM"]),
        ("BRD", "Market breadth", _p["BRD"]),
        ("IND", "Indicators & tools", r"\brsi\b|\bmacd\b|stochastic|bollinger|fibonacci|\bfib\b|volume profile|ichimoku|vwap|\batr\b|\badx\b|\bobv\b|on[- ]balance volume|divergence|indicators?|oscillators?|sentiment|point (and|&) figure|relative rotation|\brrg\b|intermarket|cmt (exam|level|program|curriculum)|technical analysis|keltner|parabolic sar|pivot points|anchored|market profile|order flow|footprint"),
    ]
    TA_PRIORITY = ["CANSLIM", "EW", "WYK", "CANDLE", "BRD", "CLASSIC", "MOM", "IND"]
    TA_DAILY_DROP = ("IND", "MOM", "CANSLIM", "CLASSIC")
TA_SUBS = TA_SUBS + [("INT", "Trader interviews", r"(?!x)x")]
TA_RE = [(k, re.compile(p, re.I)) for k, _, p in TA_SUBS]
FIGURES = json.loads((ROOT / "pipeline" / "figures.json").read_text())
FIG_RE = [(i, kind, re.compile(r"\b(" + pat + r")", re.I)) for i, (name, kind, pat) in enumerate(FIGURES)]
INTERVIEW = re.compile(r"interview|conversation|in his own words|chat(s|ting)? with|talks?\b|speaks|podcast|q ?& ?a|fireside|annual meeting|shareholder(s)? meeting|lecture|speech|keynote|address|masterclass|sits down|panel|session|\bwith\b|\bep(isode)?\.? ?#?\d+|\b#\d+\b|\bon (cnbc|bloomberg|cnn|fox business)|at (columbia|stanford|google|harvard|wharton|oxford|university|berkshire|the )", re.I)
NOT_INTERVIEW = re.compile(r"react(s|ion)?\b|summary|summari[sz]ed|animated|book review|\brules\b|secrets|strategy explained|in \d+ minutes|#shorts|portfolio (update|holdings)|\b13f\b|stock picks|is (buying|selling)|just (bought|sold)|\bwarns?\b|warning|crash|\bai\b|motivation|quotes|tribute|\bdies\b|death|biography|net worth|response|responds|rebuttal|what i learned from|lessons from|explained by|according to|would do|style\b|like (warren|buffett|munger|lynch)", re.I)


def figure_of(text):
    for i, kind, rx in FIG_RE:
        if rx.search(text):
            return i, kind
    return None, None


STRONG_IV = re.compile(r"interview|conversation|podcast|fireside|q ?& ?a|sits down|in his own words|annual meeting|shareholders? meeting", re.I)
WEAK_BAD = re.compile(r"\bby\b|\blike\b|tip from|added tip|inspired|approach|method|strategy|how to (invest|trade|pick)|explains? (how|why)", re.I)


def interview_fig(text, d, authors):
    i, kind = figure_of(text)
    if i is None or NOT_INTERVIEW.search(text) or not INTERVIEW.search(text):
        return None, None
    if not STRONG_IV.search(text) and WEAK_BAD.search(text):
        return None, None
    if (d or 0) < 600 and not authors:
        return None, None
    return i, kind


TA_EDU = re.compile(r"course|lesson|lecture|explained|tutorial|how to|introduction|intro to|principles|basics|beginners?|guide|masterclass|webinar|\bclass\b|rules|step[- ]by[- ]step|what is|understanding|learn", re.I)
MON = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*"
TA_SESSION = re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b|\b\d{4}[./-]\d{1,2}[./-]\d{1,2}\b|\b\d{1,2}(st|nd|rd|th)? " + MON + r"\b|\b" + MON + r" \d{1,2}(st|nd|rd|th)?,? \d{4}|\b\d{7}\b|prediction|forecast|for tomorrow|update\b|\blive\b|alert|elliott elite|tradefinder|nifty|tape reading lab|market discussion|discord|weekly (review|outlook|recap)|#stocks|gaming|members?'? (video|weekend|webinar)|q ?& ?a session", re.I)
TA_DAILY = re.compile(r"the final bar|stock market today|your daily five|market update|market outlook|market recap|weekly market|morning (call|show)|\(\d{1,2}[./]\d{1,2}[./]\d{2,4}\)|\b\d{1,2}/\d{1,2}/\d{2,4}\b|live trading|pre-?market|watchlist|stocks? to watch|chart this|stocks (rally|fall|slide|rise|sell off|jump)|dow jones|futures (rise|fall)", re.I)


def ta_of(text, pl_text):
    sc = {k: 2 * len(rx.findall(text)) + len(rx.findall(pl_text)) for k, rx in TA_RE}
    best = max(TA_PRIORITY, key=lambda k: (sc[k], -TA_PRIORITY.index(k)))
    return [t[0] for t in TA_SUBS].index(best) + 1 if sc[best] else 0
LEVEL_RE = [(3, re.compile(r"level\s*(iii|3)\b|\bl\s?3\b|\blvl\s*3|cfa\s*(iii|3)\b|level three", re.I)),
            (2, re.compile(r"level\s*(ii|2)\b|\bl\s?2\b|\blvl\s*2|cfa\s*(ii|2)\b|level two", re.I)),
            (1, re.compile(r"level\s*(i|1)\b|\bl\s?1\b|\blvl\s*1|cfa\s*(i|1)\b|level one", re.I))]
OTHER_CERT = re.compile(r"\bfrm\b|\bcpa\b|\bacca\b|\bcma\b|\bcmt\b|\bcaia\b|\bca (final|inter|foundation)\b|\bicai\b|class (11|12)|\bb\.?com\b|\bupsc\b|\bcs (exe|prof)|\bjee\b|\bneet\b|\bnism\b|\bcfp\b|\bcpe\b|\bfmva\b|\bsat\b|\bgmat\b|#shorts|actuarial|exam fm\b|\bsoa\b", re.I)
CFA_RE = re.compile(r"\bcfa\b|level\s*(i{1,3}|[123])\b", re.I)
DEVANAGARI = re.compile(r"[ऀ-ॿ]")
MUSIC = re.compile(r"official (music |lyric )?video|\blyrics?\b|\(official audio\)|remaster|\bft\.|music video", re.I)
NOISE = re.compile(r"research challenge|success story|testimonial|toppers? talk|live stream|livestream|webinar recording|happy (new year|diwali)|giveaway|podcast ep", re.I)


def topic_of(text, pl_text):
    scores = Counter()
    for k, _, rx in TOPIC_RE:
        scores[k] += 2 * len(rx.findall(text)) + len(rx.findall(pl_text))
    if not scores or max(scores.values()) == 0:
        return None
    curr = {k: v for k, v in scores.items() if k != "EXAM" and v}
    if curr:
        return max(curr, key=lambda k: (curr[k], -[t[0] for t in TOPICS].index(k)))
    return "EXAM"


def level_of(text, pl_text):
    for txt in (text, pl_text):
        hits = [lv for lv, rx in LEVEL_RE if rx.search(txt)]
        if len(hits) == 1:
            return hits[0]
        if hits:
            return 0
    return 0


FIN_SUBS = {"CFA", "ValueInvesting", "SecurityAnalysis"}


def load_reddit():
    mentions = defaultdict(list)
    ch_mentions = defaultdict(set)
    pl_mentions = defaultdict(set)
    for f in RAW.glob("reddit_*_*_*.jsonl"):
        for line in f.open():
            r = json.loads(line)
            if (r.get("author") or "[deleted]") in ("AutoModerator",):
                continue
            who = r.get("author") or r["id"]
            if r["kind"] == "comments":
                url = f"https://www.reddit.com/r/{r['sub']}/comments/{r.get('link_id', 't3_')[3:]}/_/{r['id']}/"
            else:
                url = f"https://www.reddit.com{r['permalink']}" if r.get("permalink") else f"https://www.reddit.com/r/{r['sub']}/comments/{r['id']}/"
            for v in r["videos"]:
                mentions[v].append({"sub": r["sub"], "who": who, "score": r.get("score") or 0, "ts": r.get("ts"), "text": r["text"], "url": url})
            for c in r["channels"]:
                ch_mentions[c.lower()].add(who)
            for p in r["playlists"]:
                pl_mentions[p].add(who)
    return mentions, ch_mentions, pl_mentions


def clean_quote(text, vid):
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    t = re.sub(r"https?://\S+", "", t)
    t = re.sub(r"(?<![\w/])/?u/[A-Za-z0-9_-]{2,}", "", t)
    t = re.sub(r"[*_>#`~]+", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:320] + ("…" if len(t) > 320 else "")


def top_quotes(red):
    seenq, qs = set(), []
    for m in sorted(red, key=lambda m: -(m["score"] or 0)):
        q = clean_quote(m["text"], None)
        if len(q) < 25 or m["who"] in seenq:
            continue
        seenq.add(m["who"])
        qs.append([q, m["url"], m["score"]])
        if len(qs) == 3:
            break
    return qs


def main():
    chans = json.loads((ROOT / "pipeline" / "channels.json").read_text())
    tiers = {c["id"]: c.get("tier") for c in chans}
    excluded = {c["id"] for c in chans if VARIANT in c.get("exclude", [])}
    mentions, ch_mentions, pl_mentions = load_reddit()

    extra = {}
    xf = RAW / "reddit_videos_meta.jsonl"
    if xf.exists():
        for line in xf.open():
            m = json.loads(line)
            extra[m["id"]] = m

    channels, ch_index = [], {}
    videos, playlists = {}, []

    def ch_idx(cid, name, subs=None, handle=None, scope="community"):
        if cid not in ch_index:
            ch_index[cid] = len(channels)
            channels.append({"id": cid, "n": name, "h": handle, "subs": subs, "scope": scope, "tier": tiers.get(cid)})
        return ch_index[cid]

    def add_video(e, ci, scope, pl_title=""):
        vid = e["id"]
        v = videos.get(vid)
        if v is None:
            v = videos[vid] = {"id": vid, "t": e.get("title") or "", "c": ci, "d": e.get("duration"), "views": e.get("view_count"),
                               "ts": e.get("timestamp"), "pl": set(), "scope": scope}
        else:
            for k, src in (("d", "duration"), ("views", "view_count"), ("ts", "timestamp")):
                if v.get(k) is None and e.get(src) is not None:
                    v[k] = e[src]
        if pl_title:
            v["pl"].add(pl_title)
        return v

    for f in sorted((RAW / "channels").glob("*.json")):
        d = json.loads(f.read_text())
        if d["id"] in excluded:
            continue
        ci = ch_idx(d["id"], d["name"], d.get("channel_follower_count"), d.get("uploader_id"), d["scope"])
        for e in d["videos"]:
            add_video(e, ci, d["scope"])
        for p in d["playlists"]:
            vs = [add_video(e, ci, d["scope"], p["title"]) for e in p["videos"] if e.get("title") not in ("[Private video]", "[Deleted video]")]
            playlists.append({"id": p["id"], "t": p["title"], "c": ci, "ids": [v["id"] for v in vs]})

    for vid, m in extra.items():
        if vid in videos or not m.get("title"):
            continue
        ci = ch_idx(m.get("channel_id") or m.get("channel"), m.get("channel") or "Unknown", m.get("channel_follower_count"), m.get("uploader_id"))
        add_video({"id": vid, "title": m["title"], "duration": m.get("duration"), "view_count": m.get("view_count"),
                   "timestamp": m.get("timestamp")}, ci, "community")

    sf = RAW / "interviews_search.jsonl"
    if sf.exists():
        for line in sf.open():
            m = json.loads(line)
            if m["id"] in videos or not m.get("title") or not m.get("channel_id"):
                continue
            fi, _ = figure_of(m["title"])
            if fi is None or FIGURES[fi][0] != m["figure"]:
                continue
            ci = ch_idx(m["channel_id"], m.get("channel") or "Unknown", scope="iv")
            add_video({"id": m["id"], "title": m["title"], "duration": m.get("duration"), "view_count": m.get("view_count")}, ci, "iv")

    out_videos, dropped = [], Counter()
    for v in videos.values():
        pl_text = " | ".join(sorted(v["pl"]))
        text = v["t"]
        red = mentions.get(v["id"], [])
        authors = len({m["who"] for m in red})
        if MUSIC.search(text):
            dropped["music"] += 1
            continue
        if not text.strip() or text in ("[Private video]", "[Deleted video]"):
            dropped["no-title"] += 1
            continue
        if v["d"] is not None and v["d"] <= 75:
            dropped["short"] += 1
            continue
        both = f"{text} {pl_text}"
        rc = len({m["who"] for m in red if m["sub"] == "CFA"})
        fi, fkind = interview_fig(text, v["d"], authors)
        if fi is not None and v["scope"] == "iv" and (v["views"] or 0) < 5000 and not authors:
            fi = None
        if fi is not None:
            if fkind == "trader":
                out_videos.append({**v, "tp": "TA", "lv": 0, "r": authors, "rc": rc, "q": top_quotes(red), "hi": 1 if DEVANAGARI.search(text) else 0,
                                   "ta": [t[0] for t in TA_SUBS].index("INT") + 1, "only": 1, "fig": fi + 1, "fa": 0, "cfa": 0})
            else:
                out_videos.append({**v, "tp": "INT", "lv": 0, "r": authors, "rc": rc, "q": top_quotes(red), "hi": 1 if DEVANAGARI.search(text) else 0, "ta": 0, "only": 0, "fig": fi + 1, "fa": FA_IDX["INT"], "cfa": 0})
            continue
        if v["scope"] == "iv":
            dropped["iv-not-interview"] += 1
            continue
        if v["scope"] != "ta" and OTHER_CERT.search(both) and not CFA_RE.search(both):
            dropped["other-cert"] += 1
            continue
        if v["scope"] != "ta" and NOISE.search(text) and not authors:
            dropped["noise"] += 1
            continue
        scope = v["scope"]
        value_only = scope == "community" and red and all(m["sub"] in ("ValueInvesting", "SecurityAnalysis") for m in red)
        if scope == "community" and red and all(m["sub"] not in FIN_SUBS for m in red):
            scope = "ta"
        if scope == "ta":
            ta = ta_of(text, pl_text)
            if ta and VARIANT == "public" and TA_SUBS[ta - 1][0] != "BRD" and TA_SESSION.search(text) and not TA_EDU.search(text) and not authors:
                dropped["ta-session"] += 1
                continue
            if ta and TA_DAILY.search(text) and TA_SUBS[ta - 1][0] in TA_DAILY_DROP and not authors:
                dropped["ta-daily-show"] += 1
                continue
            if not ta and not (authors >= 2 and v["scope"] == "community"):
                dropped["ta-offtopic"] += 1
                continue
            out_videos.append({**v, "tp": "TA", "lv": 0, "r": authors, "rc": rc, "q": top_quotes(red), "hi": 1 if DEVANAGARI.search(text) else 0,
                               "ta": ta or [t[0] for t in TA_SUBS].index(TA_PRIORITY[-1]) + 1, "only": 1, "fig": 0, "fa": 0, "cfa": 0})
            continue
        if scope == "fa":
            if FA_NOISE.search(text) or (FA_PICK.search(text) and not TA_EDU.search(text) and not authors):
                dropped["fa-stock-pick"] += 1
                continue
            fa = fa_of(text, pl_text)
            if not fa:
                dropped["fa-offtopic"] += 1
                continue
            out_videos.append({**v, "tp": "GEN", "lv": 0, "r": authors, "rc": rc, "q": top_quotes(red), "hi": 1 if DEVANAGARI.search(text) else 0,
                               "ta": 0, "only": 0, "fig": 0, "fa": fa, "cfa": 0})
            continue
        tp = topic_of(text, pl_text)
        if not tp and CFA_RE.search(both):
            tp = "EXAM"
        lv = level_of(text, pl_text)
        if scope == "broad" and (not tp or tp == "EXAM") and not authors:
            dropped["broad-offtopic"] += 1
            continue
        if scope == "mixed" and not CFA_RE.search(both) and not tp and not authors:
            dropped["mixed-offtopic"] += 1
            continue
        if scope == "mixed" and not CFA_RE.search(both) and tp in ("EXAM", "EQ") and not authors and not v["pl"]:
            dropped["mixed-commentary"] += 1
            continue
        if value_only and not (tp in ("EQ", "FSA", "CI", "PM", "ECO") and authors >= 2):
            dropped["value-offtopic"] += 1
            continue
        if scope == "community" and not (CFA_RE.search(both) or tp):
            dropped["community-offtopic"] += 1
            continue
        cfa = 1 if (scope == "cfa" or CFA_RE.search(both) or lv) else 0
        exam_meta = re.search(r"\bexam\b|study|registration|candidates?|pass(ed|ing)?\b|results?\b|level [123i]+ (now|is)|curriculum|mock|deferr", text, re.I)
        fa = (fa_of(text, pl_text) if tp not in ("EXAM", "GEN", "ETH", None) and not exam_meta else 0) if cfa else (fa_of(text, pl_text) or FA_IDX.get(TP_TO_FA.get(tp or ""), 0))
        if VARIANT == "public" and not cfa and (FA_NOISE.search(text) or (FA_PICK.search(text) and not TA_EDU.search(text) and not authors)):
            fa = 0
        if VARIANT == "public" and not cfa and not fa and tp != "TA":
            dropped["fin-offtopic"] += 1
            continue
        out_videos.append({**v, "tp": tp or "GEN", "lv": lv, "r": authors, "rc": rc, "q": top_quotes(red),
                           "hi": 1 if DEVANAGARI.search(text) else 0, "ta": (ta_of(text, pl_text) or [t[0] for t in TA_SUBS].index(TA_PRIORITY[-1]) + 1) if tp == "TA" else 0, "only": 0, "fig": 0,
                           "fa": fa, "cfa": cfa})

    used_ch = {v["c"] for v in out_videos}
    ch_videos = Counter(v["c"] for v in out_videos)
    ch_reddit = defaultdict(set)
    for v in out_videos:
        for m in mentions.get(v["id"], []):
            ch_reddit[v["c"]].add(m["who"])
    for i, c in enumerate(channels):
        for key in filter(None, [c.get("h"), c["id"]]):
            ch_reddit[i] |= ch_mentions.get(key.lower(), set())
        c["r"] = len(ch_reddit[i])
        c["nv"] = ch_videos[i]

    curated = [c for i, c in enumerate(channels) if c["scope"] not in ("community", "iv") and i in used_ch]
    for c in curated:
        if c["tier"]:
            continue
        s = 3 * math.log1p(c["r"]) + 0.35 * math.log10((c["subs"] or 1)) + 0.3 * math.log1p(c["nv"]) + {"cfa": 1.2, "mixed": 0.6}.get(c["scope"], 0)
        c["_s"] = s
    cuts = [("S", 0.15), ("A", 0.4), ("B", 0.75), ("C", 1.0)]
    for group in (lambda c: c["scope"] != "ta", lambda c: c["scope"] == "ta"):
        ranked = sorted([c for c in curated if "_s" in c and group(c)], key=lambda c: -c["_s"])
        for j, c in enumerate(ranked):
            frac = (j + 1) / max(1, len(ranked))
            c["tier"] = next(t for t, f in cuts if frac <= f + 1e-9)
    for c in channels:
        if c["scope"] == "community":
            c["tier"] = "R"
        if c["scope"] == "iv":
            c["tier"] = "I"
        c.pop("_s", None)

    remap = {old: new for new, old in enumerate(sorted(used_ch, key=lambda i: ("SABCDRI".index(channels[i]["tier"] or "R"), -(channels[i]["r"]), channels[i]["n"].lower())))}
    new_channels = [None] * len(remap)
    for old, new in remap.items():
        c = channels[old]
        new_channels[new] = [c["id"], c["n"], c.get("h") or "", c.get("subs") or 0, c["tier"], c["scope"], c["r"], c["nv"]]

    tkeys = [t[0] for t in TOPICS] + ["GEN"]
    out_videos.sort(key=lambda v: (-v["r"], -(v["views"] or 0)))
    vidx = {v["id"]: i for i, v in enumerate(out_videos)}
    rows = [[v["id"], v["t"], remap[v["c"]], int(v["d"] or 0), int(v["views"] or 0), int(v["ts"] or 0),
             v["lv"], tkeys.index(v["tp"]), v["r"], v["hi"], v["ta"], v["only"], v["fig"], v["rc"], v["fa"], v["cfa"]] for v in out_videos]
    quotes = {v["id"]: v["q"] for v in out_videos if v["q"]}

    pls_out = []
    for p in playlists:
        ids = [i for i in p["ids"] if i in vidx]
        if len(ids) < 3 or len(ids) < 0.4 * len(p["ids"]):
            continue
        tc = Counter(rows[vidx[i]][7] for i in ids)
        lc = Counter(rows[vidx[i]][6] for i in ids if rows[vidx[i]][6])
        lv = level_of(p["t"], "") or (lc.most_common(1)[0][0] if lc and lc.most_common(1)[0][1] >= 0.6 * len(ids) else 0)
        tpk = topic_of(p["t"], "")
        tp = tkeys.index(tpk) if tpk else tc.most_common(1)[0][0]
        if all(rows[vidx[i]][11] for i in ids):
            tp = tkeys.index("TA")
        tac = Counter(rows[vidx[i]][10] for i in ids if rows[vidx[i]][10])
        pr = len(pl_mentions.get(p["id"], set()))
        pls_out.append([p["id"], p["t"], remap[p["c"]], lv, tp, pr, [vidx[i] for i in ids], tac.most_common(1)[0][0] if tac else 0])
    pls_out.sort(key=lambda p: (-p[5], -sum(rows[i][8] for i in p[6]), -len(p[6])))

    data = {"built": int(time.time()), "topics": [[t[0], t[1]] for t in TOPICS] + [["GEN", "General"]],
            "ta_subs": [[t[0], t[1]] for t in TA_SUBS],
            "figures": [[f[0], f[1]] for f in FIGURES],
            "fa_subs": [[t[0], t[1]] for t in FA_SUBS],
            "channels": new_channels, "videos": rows, "playlists": pls_out, "quotes": quotes,
            "fields": {"videos": ["id", "title", "channel", "duration", "views", "timestamp", "level", "topic", "reddit_recommenders", "hindi", "ta_subtopic", "ta_only", "figure", "rcfa_recommenders", "fa_section", "in_cfa"],
                       "channels": ["id", "name", "handle", "subscribers", "tier", "scope", "reddit_recommenders", "videos"],
                       "playlists": ["id", "title", "channel", "level", "topic", "reddit_recommenders", "video_indexes", "ta_subtopic"]}}
    SITE.mkdir(exist_ok=True)
    (SITE / "videos.json").write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False))
    lv = Counter(r[6] for r in rows)
    tp = Counter(data["topics"][r[7]][0] for r in rows)
    print(f"videos {len(rows)} | channels {len(new_channels)} | playlists {len(pls_out)} | with r/CFA recs {sum(1 for r in rows if r[8])}")
    print("levels", dict(lv)); print("topics", dict(tp)); print("dropped", dict(dropped))
    print("tiers", Counter(c[4] for c in new_channels))
    print("fa", Counter(FA_SUBS[r[14] - 1][0] for r in rows if r[14]), "cfa", sum(r[15] for r in rows))
    print("ta", Counter(TA_SUBS[r[10] - 1][0] for r in rows if r[10]), "ta-only", sum(r[11] for r in rows))


if __name__ == "__main__":
    main()
