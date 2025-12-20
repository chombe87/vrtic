napravi mi python scriptu koja ce kada je pokrenem odraditi sledece:

sa stranice url: https://www.predskolska.rs/jelovnik-{monthName}-{yyyy}/ ce pokupiti izmenu jelovnika i pokusati da parsira i razdeli po obrocima.
zatim ce sa adrese https://www.predskolska.rs/wp-content/uploads/2025/11/%D0%88%D0%95%D0%9B%D0%9E%D0%92%D0%9D%D0%98%D0%9A-%D0%97%D0%90-%D0%94%D0%95%D0%A6%D0%95%D0%9C%D0%91%D0%90%D0%A0-2025.pdf skinuti pdf fajl i iz njega takodje da uradi parsiranje i razdeli na dane i obroke (d-dorucak, u-uzina, r-rucak)

zatim ce iz https://www.predskolska.rs/wp-content/uploads/2024/12/%D0%A1%D0%90%D0%A1%D0%A2%D0%90%D0%92-%D0%9D%D0%90%D0%9C%D0%98%D0%A0%D0%9D%D0%98%D0%A6%D0%90-%D0%A3-%D0%88%D0%95%D0%9B%D0%98%D0%9C%D0%90-13.12.2024.pdf takodje uraditi parsiranje

fokusiraj se da jako dobro uradis parsiranje, bez toga dalji posao nema mnogo smisla

na kraju sve ove podatke da sacuva u neke json fajlove i da napravi index.html koji ce prikazati te podatke na sledeci nacin:

-lep kalendar gde mogu da izaberem bilo koji dan za tekuci mesec, a po default da bude odabran danasnji
-kako se krecem po danima tako mi izlistava obroke i za njih sastav sastav namirnica koji match-uje, tj pronadje po nazivu i kljucnim recima

-dodaj da mogu da se krecem po danima sledeci/prethodni i ako nisam na danasnjem da je enabled dugme [danas]
-ispravi malo da se vidi nekako ceo jelovnik, poredjaj obroke sa leva na desno

-premesti da obroci budu levo a kalendar desno, smanji sve za nekih 10% da mogu obroci da stanu jedan PORED drugog, sa leva na desno
-ako si nasao nesto u izmeni to samo uokviri i prikazu u kartici za taj obrok, podatke iz originalnog menija nemoj ni da prikazes

-kalendar pomeri da bude gore iznad obroka, znaci levo je taj kao header a desno kalendar, a ispod njih su obroci koji uvek mogu da stanu sva 4 u sirinu

-sada je ono sto je glavno, a to su obroci, otislo skroz dole, i nije vidljivo. hajde rasiri malo ceo page, zatim uklopi da se vidi to sve pri otvaranju

-smanji kalendar i prebaci detalje dana skroz dole, a obroke upakuj u liniji sa kalendarom
-namesti da detalji dana budu fixed position, a ako obrok bude velik neka ide scrol za taj deo ali kada user radi scrol da detalji dana ostanu fixed

[NOVO]-smanji detalje dana da budu iste sirine kao i kalendar i postavi ispod kalendara odmah i onda nece biti daljih problema ako naraste content obroka

-rasiri povecaj jos malo ceo page
-detalji dana neka budu iznad kalendara i rasiri da kalendar i detalji dana budu siri za 100px a samim tim smanji malo sirinu obroka
-kalendar i "detalji dana" moraju biti iste sirine
-smanji visinu detalja dana za 50%
-na dnu stranice dodaj i orihnalne kompletno iscitane jelovnike i sastav namirnica ako algoritam ne nadje da user moze da radi search
-moze se desiti da ima 2 dorucka u izmeni, jedan se odnosi na jedne vrtice drugi na druge vrtice, imas ispod spisak vrtica, pokusaj i to da parsiras i da prikazes sitnim slovima na koje vrtice se odnosi
-izbaci ispis ovoga "ДОБИЈАЈУ СЛЕДЕЋИ ВРТИЋИ:", dovoljno je samo sitnim slovima kako si lepo stavio "vrtici:"
-u kalendaru si zelenim oznacio one dane gde ima izmena, a trebalo bi narandzastim
-uradio si match za ovo obrok "ЈОГУРТ, ПАВЛАКА, ПИЛЕЋА ПРСА У ОМОТУ, ХЛЕБ", sa sastavom namirnica "ПИЛЕЋА СУПА", to nema logike pokusaj da ispravis da ne nalazi previse jela u sastavima ali ipak da bude optimalno. Recimo "Рижото са свињским месом, хлеб, салата кисели краставац Ручак" bi trebalo da metchuje sa "РИЖОТО" i "РИЖОТО СА СВИЊСКИМ, ЈУНЕЋИМ ИЛИ ПИЛЕЋИМ МЕСОМ", a ne sa "ТЕСТЕНИНА СА МЕСОМ"
-dodaj kada radim search dole u [Pretraga po nazivu obroka, datumu ili namirnici], da ako kucam na latinici da konveruje u cirilicu i onda trazi
-probaj jos i kada kucam na latinici npr "rizoto" da nadje rižoto (da radi ošišana latinica, to su č-c, ć-c, š-s, ž-z, đ-dj, dž-dz...), probaj to nekako optimalno, pametan si ti
-u prikazu obroka na kraju naziva obroko si dodao svuda Rucak, Dorucak, Uzina...to je nepotrebno jer je svakako naslov vec definisan
-kod svakog obroka na kraju imas visak:
Јогурт, крем сир, стишњена шунка у омоту, хлеб Доручак - visak je "Доручак"
Воћни јогурт Ужина - visak je "Ужина"
Рижото са свињским месом, хлеб, салата кисели краставац Ручак - visak je "Ручак"
Јабуке Ужина - visak je "Ужина"
-problem je izgleda u python scripti, ovo sam pronasao u json fajlu:
        {
          "code": "u",
          "text": "Јабуке Ужина Контакт телефони централне кухиње: 021/2102747 и 021/210274",
          "calories": [
            79.5
          ],
          "raw": "У- Јабуке Ужина –79,5kcal"
        }
napravi izmene u scripti tako da se ovaj nepotrbni tekst ne nalazi ovde