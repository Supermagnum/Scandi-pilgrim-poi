# OSM comparison of Pilegrimsleden shelter/cabin POIs

Read-only comparison. Nothing was uploaded to OpenStreetMap.

Existing OSM objects were filtered from Geofabrik extracts `norway-latest.osm.pbf` and `sweden-latest.osm.pbf` (Norway plus the Swedish stretch of St. Olavsleden).

## Reference tagging (changeset 187258738)

Named pilgrim centers in changeset 187258738 are tagged as tourism=information + information=office + pilgrimage=stamp_office. That combination is the reference scheme. Nodes that only received opening_hours in this changeset are not the pilgrim-center objects.

Canonical combination:

- `tourism=information`
- `information=office`
- `pilgrimage=stamp_office`

Changeset comment: Joined, fixed opening hours , note: https://community.openstreetmap.org/t/inconsistent-tagging-for-pilgrim-centers/146312
Changeset source: https://www.pilegrimsleden.no

## Totals

Overall unique POIs: 387
matched: 139  possible: 32  gap: 216

### matched (unique POIs per trail; multi-type counted in each type column)
trail               total  Gapahuk  Pilegrimsherberge  Vandrerhjem  Rom og hytter  Rorbu  Pilegrimsbu  Dagsturhytte  Campingplass  Glamping  Teltplass  Rasteplass
------------------  -----  -------  -----------------  -----------  -------------  -----  -----------  ------------  ------------  --------  ---------  ----------
Gudbrandsdalsleden  66     12       21                 12           28             0      0            0             16            0         25         1         
St. Olavsleden      16     4        7                  0            4              0      0            0             2             0         1          0         
Borgleden           6      1        1                  1            2              0      0            0             3             0         2          2         
Kystpilegrimsleia   18     3        5                  2            4              0      0            0             5             0         1          0         
Tunsbergleden       13     3        1                  1            6              0      0            0             2             0         4          3         
Østerdalsleden      12     0        1                  4            8              0      0            0             1             0         1          0         
Valldalsleden       9      0        1                  1            9              0      0            0             2             0         2          0         
Romboleden          3      1        1                  0            1              0      0            0             0             0         0          0         
Nordleden           1      0        0                  0            1              0      0            0             0             0         1          0         
unassigned          0      0        0                  0            0              0      0            0             0             0         0          0         

### possible
trail               total  Gapahuk  Pilegrimsherberge  Vandrerhjem  Rom og hytter  Rorbu  Pilegrimsbu  Dagsturhytte  Campingplass  Glamping  Teltplass  Rasteplass
------------------  -----  -------  -----------------  -----------  -------------  -----  -----------  ------------  ------------  --------  ---------  ----------
Gudbrandsdalsleden  15     2        7                  1            3              0      0            0             2             0         4          2         
St. Olavsleden      8      0        2                  0            4              0      0            0             2             0         1          0         
Borgleden           2      0        0                  0            0              0      0            0             1             0         1          0         
Kystpilegrimsleia   2      0        1                  0            0              0      0            0             1             0         0          0         
Tunsbergleden       2      0        0                  0            1              0      0            0             0             0         1          0         
Østerdalsleden      2      0        0                  0            2              0      0            0             1             0         0          0         
Valldalsleden       4      0        0                  2            2              0      0            0             1             0         0          0         
Romboleden          1      0        0                  0            0              0      0            0             0             0         1          0         
Nordleden           1      0        1                  0            0              0      0            0             0             0         0          0         
unassigned          0      0        0                  0            0              0      0            0             0             0         0          0         

### gap
trail               total  Gapahuk  Pilegrimsherberge  Vandrerhjem  Rom og hytter  Rorbu  Pilegrimsbu  Dagsturhytte  Campingplass  Glamping  Teltplass  Rasteplass
------------------  -----  -------  -----------------  -----------  -------------  -----  -----------  ------------  ------------  --------  ---------  ----------
Gudbrandsdalsleden  88     9        49                 9            30             0      1            0             2             0         30         11        
St. Olavsleden      27     0        18                 1            8              0      0            0             0             0         1          0         
Borgleden           8      1        5                  0            1              0      0            0             0             0         1          2         
Kystpilegrimsleia   29     10       14                 1            4              2      0            5             0             2         0          1         
Tunsbergleden       18     1        11                 0            4              0      0            0             0             0         5          1         
Østerdalsleden      36     1        0                  3            32             0      0            0             0             0         0          0         
Valldalsleden       9      0        1                  0            7              0      0            0             1             0         1          0         
Romboleden          5      0        3                  3            0              0      0            0             0             0         0          0         
Nordleden           0      0        0                  0            0              0      0            0             0             0         0          0         
unassigned          0      0        0                  0            0              0      0            0             0             0         0          0         

## Priority gap spots

These reuse the thin spots from the CMS extract. A CMS count of zero means the official map has no such POI; OSM gaps below are CMS POIs with no nearby compatible OSM object.

### Valldalsleden / Gapahuk

No CMS POIs of this type are unmatched in OSM (either none exist in the CMS extract, or all have a nearby OSM object).

### Nordleden / Gapahuk

No CMS POIs of this type are unmatched in OSM (either none exist in the CMS extract, or all have a nearby OSM object).

### Romboleden / Campingplass

No CMS POIs of this type are unmatched in OSM (either none exist in the CMS extract, or all have a nearby OSM object).

### Nordleden / Campingplass

No CMS POIs of this type are unmatched in OSM (either none exist in the CMS extract, or all have a nearby OSM object).

### Nordleden (all categories)

No OSM gaps among the CMS shelter POIs on this trail.

## Gap list per trail

### Gudbrandsdalsleden (88 gaps)

- "Rastebu" at Farseggen #1 — Rasteplass — 59.99996,11.04954 — https://www.pilegrimsleden.no/interessepunkter/gapahuk-1
- "Rastebu" ved Farseggen #2 — Rasteplass — 59.99639,11.08434 — https://www.pilegrimsleden.no/interessepunkter/gapahuk
- Arteid Vestre — Rom og hytter | Teltplass — 60.05048,11.15303 — https://www.pilegrimsleden.no/interessepunkter/arteid-vestre
- Atelier Lefstorvet — Pilegrimsherberge — 60.83505,11.00913 — https://www.pilegrimsleden.no/interessepunkter/atelier-lefstorvet
- Audenhus - Pilegrimsherberge på Vingrom — Pilegrimsherberge — 61.02963,10.44037 — https://www.pilegrimsleden.no/interessepunkter/audenhus-pilegrimsherberge-pa-vingrom
- Aunan Gård — Pilegrimsherberge — 63.22568,10.04014 — https://www.pilegrimsleden.no/interessepunkter/aunan-gard
- Aurdal Gård — Pilegrimsherberge | Rom og hytter | Teltplass — 60.19008,10.36723 — https://www.pilegrimsleden.no/interessepunkter/aurdal-gard
- Basecamp Frich's Hjerkinn — Vandrerhjem | Teltplass — 62.22083,9.54418 — https://www.pilegrimsleden.no/interessepunkter/hjerkinnhus-vandrerhjem
- Betania Kolbu — Pilegrimsherberge | Rom og hytter | Teltplass — 60.61273,10.76770 — https://www.pilegrimsleden.no/interessepunkter/betania-kolbu
- Bittes Gjestehus — Pilegrimsherberge — 61.52753,10.13475 — https://www.pilegrimsleden.no/interessepunkter/bittes-gjestehus
- Brurbakkvegen 79 — Pilegrimsherberge | Vandrerhjem | Teltplass — 60.40838,10.51077 — https://www.pilegrimsleden.no/interessepunkter/brurbakkvegen-79
- Bryggerhuset Nordre Ullern — Pilegrimsherberge | Rom og hytter | Teltplass | Rasteplass — 60.08235,10.22033 — https://www.pilegrimsleden.no/interessepunkter/bryggerhuset-nordre-ullern
- Bryggerhuset på Lander — Pilegrimsherberge — 60.38972,10.51099 — https://www.pilegrimsleden.no/interessepunkter/bryggerhuset-pa-lander
- Bryhni Søndre – Gjestegård — Pilegrimsherberge — 60.72869,11.25644 — https://www.pilegrimsleden.no/interessepunkter/bryhni-sondre-gjestegard
- Brynn i Bergsengroa — Pilegrimsherberge | Teltplass — 61.03644,10.48744 — https://www.pilegrimsleden.no/interessepunkter/overnatting-pa-brynn-i-bergsengroa-i-brottum
- Båkinn Gård — Pilegrimsherberge | Rom og hytter | Teltplass | Gapahuk — 60.73660,10.82937 — https://www.pilegrimsleden.no/interessepunkter/bakinn-gard
- Bøndernes Hus Jevnaker — Gapahuk — 60.25299,10.42933 — https://www.pilegrimsleden.no/interessepunkter/bondernes-hus-jevnaker
- Dalum herberge tilbyr enkel overnatting til pilegrimer — Pilegrimsherberge — 61.68054,9.56783 — https://www.pilegrimsleden.no/interessepunkter/dalum-herberge-tilbyr-enkel-overnatting-til-pilegrimer
- Dovregubbens Hall — Vandrerhjem — 62.17461,9.42887 — https://www.pilegrimsleden.no/interessepunkter/dovregubbens-hall
- Eidsvoll gamle prestegård - STENGT I 2026 — Pilegrimsherberge | Teltplass — 60.31977,11.24586 — https://www.pilegrimsleden.no/interessepunkter/eidsvoll-gamle-prestegard
- Engen kloster i Kolbu — Pilegrimsherberge — 60.58950,10.71974 — https://www.pilegrimsleden.no/interessepunkter/engen-kloster-i-kolbu-overnatting
- Enkel overnatting i gapahuk/hytte — Gapahuk — 60.38059,11.27596 — https://www.pilegrimsleden.no/interessepunkter/enkel-overnatting-i-gapahuk-hytte
- Fjellheim gård — Pilegrimsherberge | Teltplass — 60.03787,11.14322 — https://www.pilegrimsleden.no/interessepunkter/fjellheim-gard
- Fuglesang herberge — Pilegrimsherberge — 59.92386,10.63653 — https://www.pilegrimsleden.no/interessepunkter/fuglesang-herberge-2
- Gamleveien 60 — Rom og hytter | Teltplass — 60.21534,10.37595 — https://www.pilegrimsleden.no/interessepunkter/gamleveien-60
- Gapahuk "Pilegrimshvile" — Gapahuk — 59.96628,10.95100 — https://www.pilegrimsleden.no/interessepunkter/gapahuk-pilegrimshvile
- Gapahuk i Klokkerhavna — Teltplass | Gapahuk — 60.36742,10.53755 — https://www.pilegrimsleden.no/interessepunkter/gapahuk-i-klokkerhavna
- Gapahuk på Lindeberg etter Vilbergfjellet, før Arteid — Gapahuk — 60.04271,11.15361 — https://www.pilegrimsleden.no/interessepunkter/gapahuk-pa-lindeberg-etter-vilbergfjellet-for-arteid
- Gardlaus Markastue og pilegrimsherberge — Rom og hytter — 59.93382,10.55391 — https://www.pilegrimsleden.no/interessepunkter/garlaus-markastue-og-pilegrimsherberge
- Gjesvold Gård — Pilegrimsherberge | Rom og hytter | Teltplass — 60.07363,10.27930 — https://www.pilegrimsleden.no/interessepunkter/gjesvold-gard
- Hagevandring Nordre Toten — Pilegrimsherberge | Teltplass — 60.74690,10.76175 — https://www.pilegrimsleden.no/interessepunkter/hagevandring-nordre-toten
- Haug pilegrimsrast og herberge — Rom og hytter | Teltplass — 60.34063,11.28853 — https://www.pilegrimsleden.no/interessepunkter/haug-pilegrimsrast-og-herberge
- Helgaker Gård — Rom og hytter — 60.37911,10.53496 — https://www.pilegrimsleden.no/interessepunkter/helgaker-gard
- Hoffsvangen Bygdestue — Pilegrimsherberge | Vandrerhjem | Teltplass | Rasteplass — 60.68503,10.84359 — https://www.pilegrimsleden.no/interessepunkter/hoffsvangen
- Hos Margit — Pilegrimsherberge — 61.54130,10.12501 — https://www.pilegrimsleden.no/interessepunkter/hos-margit-herberge-ovenfor-ringebu-sentrum
- Huset i skogen — Rom og hytter — 60.47002,10.57522 — https://www.pilegrimsleden.no/interessepunkter/huset-i-skogen
- Hytte på Gørdammen — Rom og hytter | Gapahuk — 60.66389,11.17566 — https://www.pilegrimsleden.no/interessepunkter/gordammen-hytte-og-gapahuk
- Indal Forest Retreat — Rom og hytter | Teltplass — 60.88077,10.66185 — https://www.pilegrimsleden.no/interessepunkter/indal-forest-retreat
- Ingeborg Refling Hagens kulturhus Fredheim — Pilegrimsherberge — 60.62121,11.25245 — https://www.pilegrimsleden.no/interessepunkter/fredheim
- InnomHaug pilegrimsherberge — Teltplass — 60.14699,11.14216 — https://www.pilegrimsleden.no/interessepunkter/innomhaug
- Jomfruburet & Drengstua — Pilegrimsherberge | Rom og hytter — 60.36562,10.53679 — https://www.pilegrimsleden.no/interessepunkter/jomfruburet-drengstua
- Jørundgard Viking- og Middelaldersenter — Rom og hytter — 61.84548,9.43461 — https://www.pilegrimsleden.no/interessepunkter/jorundgard-middelaldersenter
- Kaldor Gård - overnatting og utsikt i Hafjell — Pilegrimsherberge — 61.23446,10.46146 — https://www.pilegrimsleden.no/interessepunkter/kaldor-gard-overnatting-og-utsikt-i-hafjell
- Klokkargården Halstad — Pilegrimsherberge — 61.50589,10.17742 — https://www.pilegrimsleden.no/interessepunkter/klokkargarden-halstad
- Konstadtunet — Pilegrimsherberge — 63.22980,10.12651 — https://www.pilegrimsleden.no/interessepunkter/konstadtunet
- Kronprinsens utsikt — Gapahuk | Rasteplass — 60.05325,10.32315 — https://www.pilegrimsleden.no/interessepunkter/kronprinsens-utsikt
- Kveldsro ved Fløyta — Pilegrimsherberge | Rom og hytter — 60.42146,11.28441 — https://www.pilegrimsleden.no/interessepunkter/kveldsro-ved-floyta
- Langklopp Fjellgård — Vandrerhjem — 62.72682,9.93582 — https://www.pilegrimsleden.no/interessepunkter/langklopp-fjellgard
- Lerfald gård — Pilegrimsherberge — 63.34519,10.25391 — https://www.pilegrimsleden.no/interessepunkter/lerfald-gard
- Lygnasæter — Rom og hytter — 60.45509,10.64446 — https://www.pilegrimsleden.no/interessepunkter/lygnasaeter-hotel
- Majer Gård — Pilegrimsherberge | Rom og hytter — 60.66096,10.83889 — https://www.pilegrimsleden.no/interessepunkter/majer-gard
- Majors-Alm Gård — Pilegrimsherberge | Teltplass — 60.38751,10.51897 — https://www.pilegrimsleden.no/interessepunkter/steinkjelleren
- Meslo Herberge — Pilegrimsherberge — 62.84769,9.88262 — https://www.pilegrimsleden.no/interessepunkter/meslo-herberge
- Mjuklia - overnatting på Berkåk — Vandrerhjem — 62.83428,10.00099 — https://www.pilegrimsleden.no/interessepunkter/mjuklia-overnatting-i-rennebu
- Mjøsli - glamping eller hytter — Rom og hytter — 60.49774,11.25449 — https://www.pilegrimsleden.no/interessepunkter/mjosli-glamping-eller-hytter
- Myhrer gård — Campingplass | Teltplass — 60.00891,11.11361 — https://www.pilegrimsleden.no/interessepunkter/myhrer-gard
- Nordre Helgaker Gård — Pilegrimsherberge | Rom og hytter | Teltplass — 60.37987,10.53563 — https://www.pilegrimsleden.no/interessepunkter/nordre-helgaker-gard
- Nordrum Gård — Pilegrimsherberge — 61.45407,10.21399 — https://www.pilegrimsleden.no/interessepunkter/nordrum-gard
- Oppdalsporten — Pilegrimsherberge | Teltplass — 62.65701,9.88113 — https://www.pilegrimsleden.no/interessepunkter/oppdalsporten
- Pilegrimsbua ved Granerud — Gapahuk | Pilegrimsbu — 60.48325,11.31581 — https://www.pilegrimsleden.no/interessepunkter/pilegrimsbu
- Rastebu Falang Bru — Rasteplass — 60.34112,10.45934 — https://www.pilegrimsleden.no/interessepunkter/rastebu-falang-bru
- Rastebu Høgkorset — Rasteplass — 60.47258,10.58114 — https://www.pilegrimsleden.no/interessepunkter/rastebu-hogkorset
- Rastebu Kjølvegen — Rasteplass — 60.45261,10.54907 — https://www.pilegrimsleden.no/interessepunkter/rastebu-kjolvegen
- Rastebu Sognstoppen — Rasteplass — 60.30677,10.41974 — https://www.pilegrimsleden.no/interessepunkter/rastebu-sognstoppen
- Rudsødegården — Pilegrimsherberge | Rom og hytter — 60.32899,10.45603 — https://www.pilegrimsleden.no/interessepunkter/rudsodegarden
- Sandbakken Camping - STENGT 2023 — Rom og hytter — 61.85934,9.40640 — https://www.pilegrimsleden.no/interessepunkter/sandbakken-camping
- Segard Hoel — Pilegrimsherberge | Vandrerhjem — 62.99140,9.76547 — https://www.pilegrimsleden.no/interessepunkter/segard-hoel
- Skaun menighetshus — Pilegrimsherberge — 63.25057,10.05245 — https://www.pilegrimsleden.no/interessepunkter/skaun-menighetshus
- Skogheim Pilegrimsherberge — Vandrerhjem — 63.08804,9.69762 — https://www.pilegrimsleden.no/interessepunkter/skogheim-pilegrimsherberge
- Skomakerstua — Rom og hytter | Teltplass | Rasteplass — 60.08837,10.20262 — https://www.pilegrimsleden.no/interessepunkter/skomakerstuen-1
- Skysstasjonen Høgkorsplassen — Pilegrimsherberge | Rom og hytter | Teltplass — 60.49476,10.59669 — https://www.pilegrimsleden.no/interessepunkter/skysstasjonen-hogkorsplassen
- Slettum Gård — Pilegrimsherberge — 60.87657,10.68600 — https://www.pilegrimsleden.no/interessepunkter/slettum-gard
- Solvang overnatting — Pilegrimsherberge | Teltplass — 60.36946,11.27893 — https://www.pilegrimsleden.no/interessepunkter/solvang-herberge
- Spitalen gamle skolehus - vertskap Sannfredstun — Teltplass — 60.49546,11.31886 — https://www.pilegrimsleden.no/interessepunkter/retreat-og-herberge-i-spitalen-sondre
- Stabburet på Skjefstad — Pilegrimsherberge — 63.34480,10.28598 — https://www.pilegrimsleden.no/interessepunkter/stabburdet-pa-skjefstad
- Stall Lisletta — Rom og hytter | Teltplass — 60.14813,10.29239 — https://www.pilegrimsleden.no/interessepunkter/stall-lisletta
- Stensveen — Pilegrimsherberge | Rom og hytter | Teltplass — 60.71619,10.86076 — https://www.pilegrimsleden.no/interessepunkter/stensveen
- Stokke Nedre — Rom og hytter — 60.88623,10.67675 — https://www.pilegrimsleden.no/interessepunkter/stokke-nedre
- Stugguhaugen, Fagerhaug — Pilegrimsherberge | Rom og hytter — 62.65869,9.88461 — https://www.pilegrimsleden.no/interessepunkter/stabbur-i-oppdal-sentrum
- Sveastranda Camping — Campingplass | Rom og hytter | Teltplass — 60.88893,10.67566 — https://www.pilegrimsleden.no/interessepunkter/sveastranda-camping
- Sveinhaug gård — Pilegrimsherberge — 60.90184,10.73573 — https://www.pilegrimsleden.no/interessepunkter/sveinhaug-gard
- Svorkmo skytterhus — Pilegrimsherberge | Vandrerhjem | Rasteplass — 63.18179,9.79811 — https://www.pilegrimsleden.no/interessepunkter/svorkmo-skytterhus
- Sygard Grytting - middelalderloft — Pilegrimsherberge — 61.57594,9.89244 — https://www.pilegrimsleden.no/interessepunkter/sygard-grytting-middelalderloft
- Sætrangsgata 37 — Pilegrimsherberge — 60.16025,10.29935 — https://www.pilegrimsleden.no/interessepunkter/saetrangsgata-37
- Teltplass — Teltplass — 60.46226,10.57385 — https://www.pilegrimsleden.no/interessepunkter/lavvoplass
- Vekve hyttetun — Rom og hytter — 62.59653,9.69010 — https://www.pilegrimsleden.no/interessepunkter/vekve-hyttetun
- Østre Aker pilegrimsherberge — Pilegrimsherberge — 59.92213,10.81982 — https://www.pilegrimsleden.no/interessepunkter/ostre-aker-herberge
- ØYGARDEN PILEGRIMSHERBERGE — Pilegrimsherberge — 61.83935,9.40861 — https://www.pilegrimsleden.no/interessepunkter/oygarden-pilegrimsherberge

### St. Olavsleden (27 gaps)

- Auskin Kreative Senter — Pilegrimsherberge | Rom og hytter — 63.77813,11.71298 — https://www.pilegrimsleden.no/interessepunkter/auskin-kreative-senter
- Boda borg — Pilegrimsherberge — 62.45936,16.37399 — https://www.pilegrimsleden.no/interessepunkter/boda-borg
- Borgsjö Hembygdsgård — Pilegrimsherberge — 62.54162,15.90185 — https://www.pilegrimsleden.no/interessepunkter/borgsjo-hembygdsgard
- Borås gård — Pilegrimsherberge — 63.53676,11.05672 — https://www.pilegrimsleden.no/interessepunkter/boras-gard
- Ersgard Gårdshotell med pilegrimsovernatting — Pilegrimsherberge — 63.44987,11.00752 — https://www.pilegrimsleden.no/interessepunkter/ersgard
- Frosta Strandhus — Pilegrimsherberge — 63.59926,10.70616 — https://www.pilegrimsleden.no/interessepunkter/frosta-strandhus
- Gullesviken — Pilegrimsherberge — 62.37549,16.77126 — https://www.pilegrimsleden.no/interessepunkter/gullesviken
- Hedmans fjellby — Rom og hytter — 63.31415,13.25290 — https://www.pilegrimsleden.no/interessepunkter/hedmans-stugby
- Hotell Jämtkrogen — Rom og hytter — 62.75413,15.41716 — https://www.pilegrimsleden.no/interessepunkter/hotell-jamtkrogen
- Hussborgs herrgård — Pilegrimsherberge — 62.49729,16.01755 — https://www.pilegrimsleden.no/interessepunkter/hussborgs-herrgard
- Lilla Äppelgården — Pilegrimsherberge — 62.41062,17.20963 — https://www.pilegrimsleden.no/interessepunkter/lilla-appelgarden
- Lillelunden Gård — Pilegrimsherberge — 63.50673,11.07598 — https://www.pilegrimsleden.no/interessepunkter/lillelunden-gard
- Liten hytte i Lunne — Teltplass — 63.08333,14.88333 — https://www.pilegrimsleden.no/interessepunkter/liten-hytte-i-lunne
- Markabygda kirkestue — Pilegrimsherberge — 63.63677,11.27350 — https://www.pilegrimsleden.no/interessepunkter/markabygda-kirkestue
- Medstugan, Vandrarhemmet Mejeriet — Vandrerhjem — 63.51970,12.40792 — https://www.pilegrimsleden.no/interessepunkter/medstugan-vandrarhemmet-mejeriet
- Oldervik herberge, Frosta — Pilegrimsherberge — 63.60169,10.70725 — https://www.pilegrimsleden.no/interessepunkter/oldervik-herberge-frosta
- Rombäck 611 — Rom og hytter — 62.48987,16.28486 — https://www.pilegrimsleden.no/interessepunkter/romback-611
- Sidsjö Hotell & Konferens — Pilegrimsherberge — 62.37786,17.28656 — https://www.pilegrimsleden.no/interessepunkter/sidsjo-hotell-konferens
- Skogset — Pilegrimsherberge — 63.66366,12.03095 — https://www.pilegrimsleden.no/interessepunkter/overnatting-for-pilegrimer
- St. Olavs cabin, Hållsta — Rom og hytter — 63.00315,14.95210 — https://www.pilegrimsleden.no/interessepunkter/st-olavs-cabin-hallsta
- Stabbur i Stjørdal — Pilegrimsherberge — 63.47060,10.93993 — https://www.pilegrimsleden.no/interessepunkter/stabbur-i-stjordal
- Stalltjärnstugan — Rom og hytter — 63.47466,12.55942 — https://www.pilegrimsleden.no/interessepunkter/stalltjarnstugan
- Stuga Storharrsjön — Rom og hytter — 62.68008,15.60798 — https://www.pilegrimsleden.no/interessepunkter/stuga-storharrsjon
- Sundsvalls ridklubb — Pilegrimsherberge — 62.41285,17.19807 — https://www.pilegrimsleden.no/interessepunkter/sundsvalls-ridklubb
- Valberg Slektsgård — Pilegrimsherberge — 63.55385,10.66901 — https://www.pilegrimsleden.no/interessepunkter/valberg-slektsgard
- Valum Gård Pilegrimsovernatting — Rom og hytter — 63.70263,11.13284 — https://www.pilegrimsleden.no/interessepunkter/valum-gard-pilegrimsovernatting
- Øfsti Mellom — Pilegrimsherberge — 63.45114,11.05362 — https://www.pilegrimsleden.no/interessepunkter/ofsti-mellom

### Borgleden (8 gaps)

- Bakkelund Backpackers — Rom og hytter | Teltplass — 59.68024,10.72253 — https://www.pilegrimsleden.no/interessepunkter/bakkelund-backpackers
- Berg pilegrimsherberge — Pilegrimsherberge — 59.13699,11.32989 — https://www.pilegrimsleden.no/interessepunkter/berg-pilegrimsherberge
- Gapahuk med grillplass Tobru, Halden — Gapahuk | Rasteplass — 59.15453,11.29197 — https://www.pilegrimsleden.no/interessepunkter/gapahuk-med-grillplass-tobru-halden
- Haldenhytta — Pilegrimsherberge — 59.11876,11.39357 — https://www.pilegrimsleden.no/interessepunkter/overnatting-haldenhytta
- Pilegrimsovernatting i Moss — Pilegrimsherberge — 59.41364,10.66297 — https://www.pilegrimsleden.no/interessepunkter/pilegrimsovernatting-i-moss
- Solåsen pilegrimsgård — Pilegrimsherberge — 59.50673,10.68862 — https://www.pilegrimsleden.no/interessepunkter/solasen-pilegrimsgard
- Urtegården Nordre Mørk — Rasteplass — 59.54893,10.69792 — https://www.pilegrimsleden.no/interessepunkter/urtegarden-rasteplass-og-overnatting
- Østre Aker pilegrimsherberge — Pilegrimsherberge — 59.92213,10.81982 — https://www.pilegrimsleden.no/interessepunkter/ostre-aker-herberge

### Kystpilegrimsleia (29 gaps)

- Badestranda Leiren — Gapahuk — 61.49782,5.13585 — https://www.pilegrimsleden.no/interessepunkter/badestranda-leiren
- Borgstua på Kvernes Prestegård — Pilegrimsherberge — 63.00576,7.72356 — https://www.pilegrimsleden.no/interessepunkter/borgstua-pa-kvernes-prestegard
- Brekkegarden pilegrimsherberge — Pilegrimsherberge — 62.25332,5.58502 — https://www.pilegrimsleden.no/interessepunkter/brekkegarden-pilegrimsherberge
- Dagsturhytta Gulakvila — Gapahuk | Dagsturhytte — 60.98387,5.06670 — https://www.pilegrimsleden.no/interessepunkter/dagsturhytta-gulakvila
- Dagsturhytta Havglimt — Gapahuk | Dagsturhytte — 62.10227,5.33832 — https://www.pilegrimsleden.no/interessepunkter/dagsturhytta-havglimt
- Dagsturhytta Sørefjordhytta — Gapahuk | Dagsturhytte — 61.18432,5.34277 — https://www.pilegrimsleden.no/interessepunkter/dagsturhytta-sorefjordhytta
- Fjøsen Bed & make your own breakfast — Rom og hytter — 62.65737,7.37284 — https://www.pilegrimsleden.no/interessepunkter/sekken-bed-make-your-own-breakfast
- Friluftsfyret Kvassheim — Pilegrimsherberge — 58.54404,5.68164 — https://www.pilegrimsleden.no/interessepunkter/friluftsfyret-kvassheim
- Fru Ingas Apartments — Rorbu — 62.12373,5.31313 — https://www.pilegrimsleden.no/interessepunkter/fru-ingas-apartments
- Gapahuk i Fagerdalen — Gapahuk — 63.61320,9.85315 — https://www.pilegrimsleden.no/interessepunkter/gapahuk-i-fagerdalen
- Gapahuk på Kvernes — Gapahuk — 63.00800,7.71645 — https://www.pilegrimsleden.no/interessepunkter/gapahuk-pa-kvernes
- Gjertrudstua — Rom og hytter — 63.58049,9.95617 — https://www.pilegrimsleden.no/interessepunkter/gjertrudstua
- Hatlems Hytter — Rom og hytter — 61.15020,5.17809 — https://www.pilegrimsleden.no/interessepunkter/hatlems-hytter
- Huset ved havet — Pilegrimsherberge — 58.61359,5.61755 — https://www.pilegrimsleden.no/interessepunkter/huset-ved-havet
- Jetmund Gjesteheim — Vandrerhjem — 62.03898,5.52173 — https://www.pilegrimsleden.no/interessepunkter/jetmund-gjesteheim
- Kjeldsund leirstad og gjestegard — Pilegrimsherberge | Rom og hytter | Gapahuk | Rasteplass — 62.27240,5.82584 — https://www.pilegrimsleden.no/interessepunkter/kjeldsund-pilegrimsherberge-og-leirstad
- Kråen Gard — Pilegrimsherberge | Glamping — 62.22272,5.54123 — https://www.pilegrimsleden.no/interessepunkter/kraen-gard-gardsherberge
- Kvernes på Averøy | Nøkkelsted — Pilegrimsherberge — 63.00546,7.72188 — https://www.pilegrimsleden.no/interessepunkter/kvernes-pa-averoy
- Kvile- og lesebu i Moltudalen — Gapahuk | Dagsturhytte — 62.27928,5.62712 — https://www.pilegrimsleden.no/interessepunkter/kvile-og-lesebu-i-moltudalen
- Overnatting i stabbur med fire sengeplasser på Karmøy — Pilegrimsherberge — 59.38051,5.23716 — https://www.pilegrimsleden.no/interessepunkter/historisk-stabbur-pa-karmoy
- Pilegrimsherberge i Selje prestegard — Pilegrimsherberge — 62.04452,5.34559 — https://www.pilegrimsleden.no/interessepunkter/pilegrimsherberge-i-selje-prestegard
- Reveparken hytteutleige - overnatting direkte ved Jærstrendene — Pilegrimsherberge — 58.76803,5.51254 — https://www.pilegrimsleden.no/interessepunkter/velkommen-til-overnatting-ved-jaerstrendene
- Seljebuda — Pilegrimsherberge — 62.04579,5.34302 — https://www.pilegrimsleden.no/interessepunkter/seljebuda
- Sjøglytt — Gapahuk | Dagsturhytte — 62.04485,5.35661 — https://www.pilegrimsleden.no/interessepunkter/sjoglytt
- Sula havglamping — Pilegrimsherberge | Glamping — 63.84294,8.44704 — https://www.pilegrimsleden.no/interessepunkter/sula-havglamping
- Sætren Rorbuer — Pilegrimsherberge — 62.04409,5.34327 — https://www.pilegrimsleden.no/interessepunkter/saetren-rorbuer
- Telegrafen - Moster Amfi — Pilegrimsherberge — 59.70206,5.38264 — https://www.pilegrimsleden.no/interessepunkter/telegrafen-moster-amfi
- Tunheimsfjøra logde — Rorbu — 62.08437,5.57811 — https://www.pilegrimsleden.no/interessepunkter/tunheimsfjora-logde
- Årnseth Gapahuk — Gapahuk — 63.59482,9.96253 — https://www.pilegrimsleden.no/interessepunkter/arnseth-gapahuk

### Tunsbergleden (18 gaps)

- Berger Gård — Pilegrimsherberge — 59.86458,10.47296 — https://www.pilegrimsleden.no/interessepunkter/berger-gard
- Brannåsen — Rom og hytter | Teltplass — 59.53297,10.23931 — https://www.pilegrimsleden.no/interessepunkter/brannasen
- Engøy gjestegård — Pilegrimsherberge | Teltplass — 59.14588,10.31257 — https://www.pilegrimsleden.no/interessepunkter/engoy-gjestegard
- Fuglesang herberge — Pilegrimsherberge — 59.92386,10.63653 — https://www.pilegrimsleden.no/interessepunkter/fuglesang-herberge-2
- Gapahuk ved Stordammen — Gapahuk — 59.76495,10.37592 — https://www.pilegrimsleden.no/interessepunkter/gapahuk-ved-stordammen
- Gardlaus Markastue og pilegrimsherberge — Rom og hytter — 59.93382,10.55391 — https://www.pilegrimsleden.no/interessepunkter/garlaus-markastue-og-pilegrimsherberge
- Kaupang gård — Pilegrimsherberge | Teltplass — 59.45459,10.24783 — https://www.pilegrimsleden.no/interessepunkter/kaupang-gard
- Kirkebakken Borre - midlertidig stengt — Pilegrimsherberge — 59.38305,10.45998 — https://www.pilegrimsleden.no/interessepunkter/kirkebakken-borre
- Kjølholmen på Veierland — Teltplass — 59.16480,10.36015 — https://www.pilegrimsleden.no/interessepunkter/kjolholmen-pa-veierland
- Lavvoen Biggen — Rasteplass — 59.80946,10.37525 — https://www.pilegrimsleden.no/interessepunkter/lavvoen-biggen
- Orrfuglstua pilegrimsherberge — Pilegrimsherberge — 59.42896,10.44614 — https://www.pilegrimsleden.no/interessepunkter/orrfuglstua-pilegrimsherberge
- Poppel pilegrimsherberge — Pilegrimsherberge — 59.27783,10.44163 — https://www.pilegrimsleden.no/interessepunkter/poppel-pilegrimsherberge
- Preståsen pilegrimsherberge — Pilegrimsherberge — 59.13414,10.23932 — https://www.pilegrimsleden.no/interessepunkter/sunny-place
- Røyken Menighetshus — Pilegrimsherberge — 59.74654,10.38825 — https://www.pilegrimsleden.no/interessepunkter/royken-menighetshus
- Sande overnatting — Pilegrimsherberge — 59.59076,10.20882 — https://www.pilegrimsleden.no/interessepunkter/sande-overnatting
- Tyristua — Rom og hytter | Teltplass — 59.53511,10.22556 — https://www.pilegrimsleden.no/interessepunkter/tyristua
- Veierland skole — Rom og hytter — 59.15749,10.35365 — https://www.pilegrimsleden.no/interessepunkter/veierland-skole
- Østre Aker pilegrimsherberge — Pilegrimsherberge — 59.92213,10.81982 — https://www.pilegrimsleden.no/interessepunkter/ostre-aker-herberge

### Østerdalsleden (36 gaps)

- Barmo -hus til leie — Rom og hytter — 61.75793,11.17444 — https://www.pilegrimsleden.no/interessepunkter/barmo-hus-til-leie
- Bjerkelihytten på Aasgårvollen — Rom og hytter — 62.38435,10.83800 — https://www.pilegrimsleden.no/interessepunkter/bjerkelihytten-pa-aasgarvollen
- Dagfinnstua på Oddheim — Rom og hytter — 61.05922,12.60218 — https://www.pilegrimsleden.no/interessepunkter/dagfinnstua-pa-oddheim-1
- Elgstua | Gjerfloen Fluefiske — Rom og hytter — 61.14200,12.48574 — https://www.pilegrimsleden.no/interessepunkter/elgstua
- Eltdalen Grendehus — Rom og hytter — 61.48052,11.93586 — https://www.pilegrimsleden.no/interessepunkter/grendahus-i-eltdalen
- Fagertun — Rom og hytter — 62.27298,10.77223 — https://www.pilegrimsleden.no/interessepunkter/fagertun
- Fiskvik Søndre - Jaktslottet. — Rom og hytter — 61.65316,11.16704 — https://www.pilegrimsleden.no/interessepunkter/fiksvik-sondre
- Fjellavvo ved Osdalssjøhøgda naturreservat — Rom og hytter — 61.60285,11.74543 — https://www.pilegrimsleden.no/interessepunkter/fjellavvo-ved-osdalssjohogda-naturreservat
- Flenåsstua, Ol-Jons garden — Rom og hytter — 61.32945,12.24665 — https://www.pilegrimsleden.no/interessepunkter/flenasstua-ol-jons-garden
- Fluesonen | Gjerfloen fluefiske — Vandrerhjem — 61.11619,12.53831 — https://www.pilegrimsleden.no/interessepunkter/fluesonen
- Heimvollen — Rom og hytter — 63.20358,10.43633 — https://www.pilegrimsleden.no/interessepunkter/heimvollen
- Hytte på Osåsan — Rom og hytter — 62.48051,11.12502 — https://www.pilegrimsleden.no/interessepunkter/hytte-pa-osasan
- Hytte ved Nordstu Digre — Rom og hytter — 62.96395,10.68845 — https://www.pilegrimsleden.no/interessepunkter/hytte-ved-nordstu-digre
- Hytte | Storbekkøya museumssæter — Rom og hytter — 62.79635,10.62479 — https://www.pilegrimsleden.no/interessepunkter/hytte-pa-storbekkoya-museumssaeter
- Kari Maries Sommerresidens — Rom og hytter — 62.94692,10.63472 — https://www.pilegrimsleden.no/interessepunkter/kari-maries-sommerresidens
- Kneppstua - stengt — Rom og hytter — 61.65452,11.16730 — https://www.pilegrimsleden.no/interessepunkter/kneppstua
- Koie ved Netsjøen — Rom og hytter — 61.47016,11.22728 — https://www.pilegrimsleden.no/interessepunkter/koie-ved-netsjoen
- Koie ved Nysledammen — Rom og hytter — 61.46234,11.97301 — https://www.pilegrimsleden.no/interessepunkter/koie-ved-nosledammen
- Mandfloen husmannsplass — Rom og hytter — 61.14837,12.46759 — https://www.pilegrimsleden.no/interessepunkter/mandfloen-husmannsplass
- Negarn — Rom og hytter — 61.88365,11.09024 — https://www.pilegrimsleden.no/interessepunkter/negarn
- Perskoia — Rom og hytter — 61.33740,11.39139 — https://www.pilegrimsleden.no/interessepunkter/perskoia
- Pilegrimsbu Vardan — Rom og hytter — 62.89037,10.58754 — https://www.pilegrimsleden.no/interessepunkter/pilegrimsbu-vardan
- Pilegrimsbu ved Okstjønna — Rom og hytter — 63.05022,10.67842 — https://www.pilegrimsleden.no/interessepunkter/pilegrimsbu-ved-okstjonna
- Pilegrimslavvo ved Søndre Kvanntjønna — Rom og hytter — 62.10847,10.93561 — https://www.pilegrimsleden.no/interessepunkter/pilegrimslavvo-ved-sondre-kvanntjonna
- Romenstad Gård — Vandrerhjem — 61.96764,11.10718 — https://www.pilegrimsleden.no/interessepunkter/romenstad-gard
- Samatun — Rom og hytter — 63.11049,10.59602 — https://www.pilegrimsleden.no/interessepunkter/samatun
- Simensvollen - trivelig seterstue — Rom og hytter — 62.46772,11.07105 — https://www.pilegrimsleden.no/interessepunkter/simensvollen-trivelig-seterstue
- Skårsåsbua — Rom og hytter — 62.01867,10.96339 — https://www.pilegrimsleden.no/interessepunkter/lavvo-ved-skorsasetra
- Småvangan skihytte — Rom og hytter — 62.17705,10.82265 — https://www.pilegrimsleden.no/interessepunkter/smavangan-skihytte
- Stengt- Pilegrimshytta i Otnes — Rom og hytter — 61.75815,11.17945 — https://www.pilegrimsleden.no/interessepunkter/pilegrimshytta-i-otnes
- Svarttjønnbua — Rom og hytter — 62.73524,10.76758 — https://www.pilegrimsleden.no/interessepunkter/svarttjonnbua
- Tollefkoia — Rom og hytter — 61.27510,11.44909 — https://www.pilegrimsleden.no/interessepunkter/tollefkoia
- Tollefsa Gjestegård — Vandrerhjem — 62.41785,10.85837 — https://www.pilegrimsleden.no/interessepunkter/tollefsa-gjestegard
- Trollhaugen — Rom og hytter — 62.34236,10.81301 — https://www.pilegrimsleden.no/interessepunkter/trollhaugen
- Trollhytta — Rom og hytter — 61.42528,11.30190 — https://www.pilegrimsleden.no/interessepunkter/trollhytta
- Øyvindtjønna sælehus — Gapahuk — 63.26037,10.33401 — https://www.pilegrimsleden.no/interessepunkter/oyvindtjonna-saelehus

### Valldalsleden (9 gaps)

- Elvebakken Camping — Campingplass | Teltplass — 62.30251,7.25581 — https://www.pilegrimsleden.no/interessepunkter/elvebakken-camping
- Gammelstuggu — Rom og hytter — 62.23509,8.30631 — https://www.pilegrimsleden.no/interessepunkter/gammelstuggu
- Klosteret av Den Hellige Olav — Pilegrimsherberge — 62.29989,7.29515 — https://www.pilegrimsleden.no/interessepunkter/monastery-of-saint-olav
- Koia - Hytte i Verma — Rom og hytter — 62.26956,8.07414 — https://www.pilegrimsleden.no/interessepunkter/koia-hytte-i-verma
- Kvennbekkhytta (stengt) — Rom og hytter — 62.19240,8.54058 — https://www.pilegrimsleden.no/interessepunkter/kvennbekkhytta
- Lesja Gjestgiveri — Rom og hytter — 62.11820,8.85337 — https://www.pilegrimsleden.no/interessepunkter/lesja-gjestgiveri
- Lorkverna — Rom og hytter — 62.12006,8.65121 — https://www.pilegrimsleden.no/interessepunkter/lorkverna
- Muri hytteutleige — Rom og hytter — 62.29916,7.25497 — https://www.pilegrimsleden.no/interessepunkter/muri-hytteutleige
- Sør-Einbu — Rom og hytter — 62.23909,8.30117 — https://www.pilegrimsleden.no/interessepunkter/sor-einbu

### Romboleden (5 gaps)

- Balstad pensjonat — Pilegrimsherberge | Vandrerhjem — 63.26396,10.97328 — https://www.pilegrimsleden.no/interessepunkter/balstad-pensjonat
- Bekken Pilegrimsherberge — Pilegrimsherberge — 63.19164,11.15409 — https://www.pilegrimsleden.no/interessepunkter/bekken-pilegrimsherberge
- Jensgarden — Vandrerhjem — 63.06171,11.45374 — https://www.pilegrimsleden.no/interessepunkter/jensgarden
- Neatun — Vandrerhjem — 63.03148,11.67673 — https://www.pilegrimsleden.no/interessepunkter/neatun
- Trøen gård — Pilegrimsherberge — 63.05514,11.56320 — https://www.pilegrimsleden.no/interessepunkter/troen-gard

### Nordleden (0 gaps)

None.

## Pilgrim centers already in OSM

Queried from Geofabrik Norway and Sweden extracts using the changeset 187258738 scheme (`pilgrimage=stamp_office`, plus `tourism=information` + `information=office` when the name refers to a pilgrim center, and `network=Pilegrimsleden`).

OSM pilgrim-center objects found: 35

- (unnamed) — node/6652754859 — 61.54867,9.96648 — https://www.openstreetmap.org/node/6652754859
- (unnamed) — node/6652754860 — 61.54866,9.96633 — https://www.openstreetmap.org/node/6652754860
- (unnamed) — node/8710369186 — 60.36741,10.52859 — https://www.openstreetmap.org/node/8710369186
- (unnamed) — node/8710369187 — 60.36726,10.52856 — https://www.openstreetmap.org/node/8710369187
- (unnamed) — node/8710369188 — 60.36727,10.52837 — https://www.openstreetmap.org/node/8710369188
- (unnamed) — node/8710369189 — 60.36736,10.52839 — https://www.openstreetmap.org/node/8710369189
- (unnamed) — node/8710369190 — 60.36736,10.52826 — https://www.openstreetmap.org/node/8710369190
- (unnamed) — node/8710369191 — 60.36746,10.52828 — https://www.openstreetmap.org/node/8710369191
- (unnamed) — node/8710369192 — 60.36745,10.52845 — https://www.openstreetmap.org/node/8710369192
- (unnamed) — node/8710369193 — 60.36741,10.52844 — https://www.openstreetmap.org/node/8710369193
- (unnamed) — node/9174883503 — 61.54889,9.96628 — https://www.openstreetmap.org/node/9174883503
- (unnamed) — node/9174883504 — 61.54890,9.96643 — https://www.openstreetmap.org/node/9174883504
- (unnamed) — node/9174883505 — 61.54872,9.96632 — https://www.openstreetmap.org/node/9174883505
- (unnamed) — node/9174883506 — 61.54872,9.96629 — https://www.openstreetmap.org/node/9174883506
- (unnamed) — node/9174883507 — 61.54876,9.96628 — https://www.openstreetmap.org/node/9174883507
- (unnamed) — node/9174883508 — 61.54876,9.96631 — https://www.openstreetmap.org/node/9174883508
- (unnamed) — node/9272283202 — 60.79280,11.04278 — https://www.openstreetmap.org/node/9272283202
- (unnamed) — node/9272283203 — 60.79285,11.04305 — https://www.openstreetmap.org/node/9272283203
- (unnamed) — node/9272283204 — 60.79276,11.04312 — https://www.openstreetmap.org/node/9272283204
- (unnamed) — node/9272283205 — 60.79271,11.04285 — https://www.openstreetmap.org/node/9272283205
- (unnamed) — node/9272283206 — 60.79275,11.04282 — https://www.openstreetmap.org/node/9272283206
- (unnamed) — node/9272283207 — 60.79275,11.04279 — https://www.openstreetmap.org/node/9272283207
- (unnamed) — node/9272283208 — 60.79278,11.04277 — https://www.openstreetmap.org/node/9272283208
- (unnamed) — node/9272283209 — 60.79279,11.04279 — https://www.openstreetmap.org/node/9272283209
- Nidaros Pilgrimsgård — way/167823309 — 63.42663,10.40003 — https://www.openstreetmap.org/way/167823309
- Pilegrimssenter Avaldsnes — node/14086531584 — 59.35478,5.29217 — https://www.openstreetmap.org/node/14086531584
- Pilegrimssenter Dale-Gudbrand — way/708003068 — 61.54876,9.96634 — https://www.openstreetmap.org/way/708003068
- Pilegrimssenter Dovrefjell — node/14086486197 — 62.22235,9.56834 — https://www.openstreetmap.org/node/14086486197
- Pilegrimssenter Granavollen — way/475158600 — 60.36738,10.52842 — https://www.openstreetmap.org/way/475158600
- Pilegrimssenter Hamar — way/98811698 — 60.79277,11.04286 — https://www.openstreetmap.org/way/98811698
- Pilegrimssenter Oslo — node/2785465804 — 59.90633,10.76960 — https://www.openstreetmap.org/node/2785465804
- Pilegrimssenter Smøla — node/11039992018 — 63.28641,8.13439 — https://www.openstreetmap.org/node/11039992018
- Regional Pilgrim Center Avaldsnes — node/14086526408 — 59.28317,5.30845 — https://www.openstreetmap.org/node/14086526408
- Regionalt pilegrimssenter Bergen — node/14086526409 — 60.39922,5.32250 — https://www.openstreetmap.org/node/14086526409
- Stiklestad pilegrimssenter — node/14086452092 — 63.79596,11.56195 — https://www.openstreetmap.org/node/14086452092

## OSM pilgrim centers with no corresponding Pilegrimsleden CMS entry

CMS pilgrim-center points are matched to the *closest* OSM `pilgrimage=stamp_office`
node or way within 250 m (not an arbitrary peer when several exist). Reverse checks
also accept nearby CMS map POIs that are not typed `Pilegrimssenter`.

CMS **Regionalt pilegrimssenter Avaldsnes** matches on-site
`node/14086531584` (Pilegrimssenter Avaldsnes) at 6.7 m. A second OSM stamp-office
node `14086526408` (~8 km south, named "Regional Pilgrim Center Avaldsnes") has no
CMS POI within 250 m and is an OSM duplicate/misplaced object, not a CMS Avaldsnes gap.

Named OSM stamp offices still without a CMS map POI within 250 m:

- Regional Pilgrim Center Avaldsnes — node/14086526408 — https://www.openstreetmap.org/node/14086526408 — nearest CMS: Regionalt pilegrimssenter Avaldsnes at 8012 m (https://www.pilegrimsleden.no/interessepunkter/regionalt-pilegrimssenter-avaldsnes)

## Data quality notes

Nidaros Pilgrimsgård exists correctly in OSM as a pilgrim stamp office but is filed under a non-Pilegrimssenter category on the CMS map — a CMS taxonomy inconsistency, not an OSM gap.
