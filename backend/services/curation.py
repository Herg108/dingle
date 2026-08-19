import json
import random
import threading
from pathlib import Path

from services import deezer, youtube

_resolution_lock = threading.Lock()
_resolution_running = False

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "curated_songs.json"
MAX_RESOLUTIONS_PER_CALL = 3  # YouTube's free tier is 100 searches/day and each
# resolution can cost up to 2 (a retry when no clean audio match shows up in
# the first pass) — keep this low so normal gameplay doesn't exhaust the daily
# quota just from background resolution; the full list fills in gradually.

# Hand-picked, genuinely widely-recognized songs — deliberately favoring
# universal familiarity over chart-algorithm "popularity" or personal taste.
# Tagged by decade so selection can be weighted toward recent pop while still
# keeping classics in the mix (see DECADE_WEIGHTS below).
SEED_SONGS_60S_70S = [
    ("Queen", "Bohemian Rhapsody"), ("Queen", "We Will Rock You"), ("Queen", "We Are the Champions"),
    ("Led Zeppelin", "Stairway to Heaven"), ("Eagles", "Hotel California"),
    ("Fleetwood Mac", "Dreams"), ("Fleetwood Mac", "Go Your Own Way"),
    ("Stevie Wonder", "Superstition"), ("Elton John", "Rocket Man"), ("Elton John", "Your Song"),
    ("David Bowie", "Heroes"), ("David Bowie", "Space Oddity"),
    ("ABBA", "Dancing Queen"), ("Bee Gees", "Stayin' Alive"), ("Earth, Wind & Fire", "September"),
    ("Bill Withers", "Ain't No Sunshine"), ("Bill Withers", "Lean on Me"), ("Billy Joel", "Piano Man"),
    ("The Jackson 5", "I Want You Back"), ("Donna Summer", "I Feel Love"),
    ("KC and the Sunshine Band", "Get Down Tonight"),
    ("The Beatles", "Hey Jude"), ("The Beatles", "Let It Be"), ("The Beatles", "Here Comes the Sun"),
    ("The Rolling Stones", "(I Can't Get No) Satisfaction"), ("The Beach Boys", "Good Vibrations"),
    ("Aretha Franklin", "Respect"), ("Otis Redding", "(Sittin' On) The Dock of the Bay"),
    ("The Supremes", "You Can't Hurry Love"), ("Marvin Gaye", "I Heard It Through the Grapevine"),
    ("Simon & Garfunkel", "The Sound of Silence"), ("Bob Dylan", "Like a Rolling Stone"),
    ("Elvis Presley", "Jailhouse Rock"), ("Chuck Berry", "Johnny B. Goode"),
]

SEED_SONGS_80S = [
    ("Michael Jackson", "Billie Jean"), ("Michael Jackson", "Thriller"), ("Michael Jackson", "Beat It"),
    ("Whitney Houston", "I Wanna Dance with Somebody"), ("Whitney Houston", "How Will I Know"),
    ("Madonna", "Like a Virgin"), ("Madonna", "Material Girl"),
    ("Prince", "Purple Rain"), ("Prince", "When Doves Cry"),
    ("a-ha", "Take On Me"), ("Journey", "Don't Stop Believin'"),
    ("Guns N' Roses", "Sweet Child O' Mine"), ("Bon Jovi", "Livin' on a Prayer"),
    ("Cyndi Lauper", "Girls Just Want to Have Fun"), ("Tears for Fears", "Everybody Wants to Rule the World"),
    ("Duran Duran", "Hungry Like the Wolf"), ("The Police", "Every Breath You Take"),
    ("Toto", "Africa"), ("Eurythmics", "Sweet Dreams (Are Made of This)"),
    ("Van Halen", "Jump"), ("Def Leppard", "Pour Some Sugar on Me"),
    ("INXS", "Never Tear Us Apart"), ("George Michael", "Faith"),
    ("Wham!", "Wake Me Up Before You Go-Go"), ("Phil Collins", "In the Air Tonight"),
]

SEED_SONGS_90S = [
    ("Nirvana", "Smells Like Teen Spirit"), ("Whitney Houston", "I Will Always Love You"),
    ("Mariah Carey", "All I Want for Christmas Is You"), ("TLC", "No Scrubs"), ("TLC", "Waterfalls"),
    ("Backstreet Boys", "I Want It That Way"), ("*NSYNC", "Bye Bye Bye"),
    ("Britney Spears", "...Baby One More Time"), ("Spice Girls", "Wannabe"),
    ("Alanis Morissette", "Ironic"), ("Oasis", "Wonderwall"), ("Radiohead", "Creep"),
    ("Green Day", "Basket Case"), ("Red Hot Chili Peppers", "Under the Bridge"),
    ("R.E.M.", "Losing My Religion"), ("Toni Braxton", "Un-Break My Heart"),
    ("Boyz II Men", "End of the Road"), ("Celine Dion", "My Heart Will Go On"),
    ("Shania Twain", "Man! I Feel Like a Woman!"), ("The Notorious B.I.G.", "Juicy"),
    ("2Pac", "California Love"), ("Dr. Dre", "Nuthin' but a 'G' Thang"),
    ("Coolio", "Gangsta's Paradise"), ("Beastie Boys", "Sabotage"),
    ("No Doubt", "Don't Speak"), ("Sublime", "Santeria"), ("Smash Mouth", "All Star"),
    ("Run-D.M.C.", "Walk This Way"), ("Salt-N-Pepa", "Push It"),
]

SEED_SONGS_2000S = [
    ("Beyoncé", "Crazy in Love"), ("Beyoncé", "Single Ladies (Put a Ring on It)"),
    ("Outkast", "Hey Ya!"), ("Usher", "Yeah!"), ("Eminem", "Lose Yourself"), ("Eminem", "Without Me"),
    ("Kelly Clarkson", "Since U Been Gone"), ("Avril Lavigne", "Complicated"),
    ("Christina Aguilera", "Beautiful"), ("Justin Timberlake", "Cry Me a River"),
    ("Rihanna", "Umbrella"), ("Amy Winehouse", "Rehab"),
    ("Coldplay", "Yellow"), ("Coldplay", "Clocks"), ("Green Day", "Boulevard of Broken Dreams"),
    ("Linkin Park", "In the End"), ("Evanescence", "Bring Me to Life"),
    ("Fall Out Boy", "Sugar, We're Goin Down"), ("Panic! At The Disco", "I Write Sins Not Tragedies"),
    ("Kanye West", "Stronger"), ("Black Eyed Peas", "I Gotta Feeling"),
    ("Lady Gaga", "Poker Face"), ("Lady Gaga", "Bad Romance"),
    ("Katy Perry", "Firework"), ("Katy Perry", "Teenage Dream"),
    ("Taylor Swift", "Love Story"), ("Adele", "Rolling in the Deep"),
    ("Missy Elliott", "Get Ur Freak On"), ("Destiny's Child", "Say My Name"),
    ("Alicia Keys", "No One"), ("John Legend", "All of Me"),
]

SEED_SONGS_2010S = [
    ("Adele", "Someone Like You"), ("Adele", "Hello"),
    ("Bruno Mars", "Uptown Funk"), ("Bruno Mars", "Just the Way You Are"), ("Bruno Mars", "24K Magic"),
    ("Ed Sheeran", "Shape of You"), ("Ed Sheeran", "Perfect"), ("Ed Sheeran", "Thinking Out Loud"),
    ("Ed Sheeran", "Bad Habits"),
    ("Taylor Swift", "Shake It Off"), ("Taylor Swift", "Blank Space"),
    ("Katy Perry", "Roar"), ("Pharrell Williams", "Happy"), ("Daft Punk", "Get Lucky"),
    ("Imagine Dragons", "Radioactive"), ("Imagine Dragons", "Believer"),
    ("The Weeknd", "Can't Feel My Face"), ("The Weeknd", "Blinding Lights"),
    ("Sia", "Chandelier"), ("Rihanna", "Diamonds"), ("Rihanna", "Work"), ("Rihanna", "Needed Me"),
    ("Sam Smith", "Stay With Me"), ("Lorde", "Royals"), ("Meghan Trainor", "All About That Bass"),
    ("Justin Bieber", "Sorry"), ("Justin Bieber", "Baby"), ("Justin Bieber", "Love Yourself"),
    ("Miley Cyrus", "Wrecking Ball"), ("One Direction", "What Makes You Beautiful"),
    ("Carly Rae Jepsen", "Call Me Maybe"), ("Psy", "Gangnam Style"), ("Robin Thicke", "Blurred Lines"),
    ("Drake", "Hotline Bling"), ("Drake", "God's Plan"),
    ("Post Malone", "Circles"), ("Post Malone", "Sunflower"), ("Post Malone", "rockstar"),
    ("Dua Lipa", "New Rules"), ("Dua Lipa", "Don't Start Now"),
    ("Camila Cabello", "Havana"), ("Billie Eilish", "Bad Guy"), ("Billie Eilish", "Ocean Eyes"),
    ("Ariana Grande", "Thank U, Next"), ("Ariana Grande", "7 Rings"), ("Ariana Grande", "Problem"),
    ("Ariana Grande", "Into You"),
    ("Shawn Mendes", "Stitches"), ("Charlie Puth", "Attention"),
    ("Maroon 5", "Sugar"), ("Maroon 5", "Girls Like You"),
    ("The Chainsmokers", "Closer"), ("Zedd", "The Middle"), ("Marshmello", "Happier"),
    ("Halsey", "Without Me"), ("Khalid", "Location"),
    ("Cardi B", "Bodak Yellow"), ("Lizzo", "Truth Hurts"),
    ("Walk the Moon", "Shut Up and Dance"), ("Fifth Harmony", "Work from Home"),
    ("Zayn", "Pillowtalk"), ("Shawn Mendes", "Señorita"), ("Jonas Brothers", "Sucker"),
    ("24kGoldn", "Mood"), ("Jack Harlow", "First Class"),
    ("Lil Baby", "Drip Too Hard"), ("Roddy Ricch", "The Box"),
    ("Taylor Swift", "You Belong With Me"), ("Taylor Swift", "22"),
    ("Taylor Swift", "Bad Blood"), ("Taylor Swift", "Look What You Made Me Do"),
    ("Taylor Swift", "Delicate"), ("Taylor Swift", "Style"),
    ("Taylor Swift", "Wildest Dreams"), ("Taylor Swift", "I Knew You Were Trouble"),
    ("Ariana Grande", "No Tears Left To Cry"), ("Ariana Grande", "God Is a Woman"),
    ("Ariana Grande", "Side To Side"), ("Ariana Grande", "Dangerous Woman"),
    ("Ariana Grande", "Break Free"),
    ("Katy Perry", "Dark Horse"), ("Katy Perry", "California Gurls"),
    ("Katy Perry", "Wide Awake"), ("Katy Perry", "Part Of Me"),
    ("Selena Gomez", "Come & Get It"), ("Selena Gomez", "Same Old Love"),
    ("Selena Gomez", "Bad Liar"), ("Selena Gomez", "Wolves"),
    ("Camila Cabello", "Never Be the Same"),
    ("Shawn Mendes", "Treat You Better"), ("Shawn Mendes", "There's Nothing Holdin' Me Back"),
    ("Shawn Mendes", "In My Blood"), ("Shawn Mendes", "Mercy"),
    ("Halsey", "Bad At Love"), ("Halsey", "Him & I"),
    ("Halsey", "Colors"), ("Halsey", "Now or Never"),
    ("Demi Lovato", "Sorry Not Sorry"), ("Demi Lovato", "Confident"),
    ("Demi Lovato", "Skyscraper"), ("Demi Lovato", "Heart Attack"),
    ("Kesha", "Tik Tok"), ("Kesha", "Die Young"), ("Kesha", "Praying"),
    ("Pitbull", "Timber"), ("Pitbull", "Give Me Everything"), ("Pitbull", "International Love"),
    ("Flo Rida", "Whistle"), ("Flo Rida", "Good Feeling"), ("Flo Rida", "Low"),
    ("Britney Spears", "Till the World Ends"), ("Britney Spears", "Hold It Against Me"),
    ("Sia", "Cheap Thrills"), ("Sia", "Elastic Heart"), ("Sia", "Titanium"),
    ("Sam Smith", "I'm Not the Only One"), ("Sam Smith", "Too Good at Goodbyes"),
    ("Adele", "Set Fire to the Rain"),
    ("Ed Sheeran", "Photograph"), ("Ed Sheeran", "Castle on the Hill"), ("Ed Sheeran", "Galway Girl"),
    ("Justin Bieber", "What Do You Mean?"), ("Justin Bieber", "Company"),
    ("Charlie Puth", "See You Again"), ("Charlie Puth", "We Don't Talk Anymore"),
    ("Zedd", "Clarity"), ("Marshmello", "Alone"),
    ("Calvin Harris", "Summer"), ("Calvin Harris", "This Is What You Came For"),
    ("Calvin Harris", "Feel So Close"), ("Calvin Harris", "Outside"),
    ("David Guetta", "Play Hard"),
    ("Avicii", "Wake Me Up"), ("Avicii", "Levels"), ("Avicii", "Hey Brother"),
    ("Martin Garrix", "Animals"), ("Martin Garrix", "In the Name of Love"),
    ("Major Lazer", "Lean On"), ("DJ Snake", "Turn Down for What"),
    ("The Chainsmokers", "Don't Let Me Down"), ("The Chainsmokers", "Something Just Like This"),
    ("The Chainsmokers", "Paris"),
    ("Drake", "One Dance"), ("Drake", "In My Feelings"),
    ("Drake", "Started From the Bottom"), ("Drake", "Hold On, We're Going Home"),
    ("Kendrick Lamar", "Alright"), ("Kendrick Lamar", "Swimming Pools"), ("Kendrick Lamar", "King Kunta"),
    ("Travis Scott", "Goosebumps"), ("Travis Scott", "Antidote"),
    ("Future", "Mask Off"), ("Cardi B", "I Like It"), ("Cardi B", "Money"),
    ("Megan Thee Stallion", "Hot Girl Summer"),
    ("Nicki Minaj", "Anaconda"), ("Nicki Minaj", "Super Bass"),
    ("Migos", "Bad and Boujee"), ("J. Cole", "No Role Modelz"), ("Lizzo", "Good as Hell"),
    ("SZA", "Love Galore"), ("SZA", "The Weekend"),
    ("Khalid", "Young Dumb & Broke"), ("Khalid", "Talk"),
    ("The Weeknd", "Starboy"), ("The Weeknd", "The Hills"), ("The Weeknd", "Earned It"),
    ("Frank Ocean", "Thinking Bout You"), ("Frank Ocean", "Pink + White"),
    ("Bruno Mars", "Locked Out of Heaven"), ("Bruno Mars", "Grenade"), ("Bruno Mars", "Treasure"),
    ("Daniel Caesar", "Best Part"),
    ("Luke Combs", "Hurricane"), ("Luke Combs", "Beautiful Crazy"),
    ("Kane Brown", "Heaven"), ("Chris Stapleton", "Tennessee Whiskey"),
    ("Kacey Musgraves", "Follow Your Arrow"),
    ("Florida Georgia Line", "Cruise"), ("Florida Georgia Line", "H.O.L.Y."),
    ("Sam Hunt", "Body Like a Back Road"),
    ("Luis Fonsi", "Despacito"), ("J Balvin", "Mi Gente"), ("J Balvin", "Ginza"),
    ("Bad Bunny", "Callaita"), ("Shakira", "Waka Waka (This Time for Africa)"),
    ("BTS", "Boy With Luv"), ("BLACKPINK", "Kill This Love"), ("BLACKPINK", "DDU-DU DDU-DU"),
    ("Imagine Dragons", "Thunder"), ("Imagine Dragons", "Demons"), ("Imagine Dragons", "Whatever It Takes"),
    ("Twenty One Pilots", "Stressed Out"), ("Twenty One Pilots", "Ride"), ("Twenty One Pilots", "Heathens"),
    ("Panic! At The Disco", "High Hopes"),
    ("Fall Out Boy", "Centuries"), ("Fall Out Boy", "My Songs Know What You Did in the Dark"),
    ("Cage The Elephant", "Cigarette Daydreams"), ("Foster The People", "Pumped Up Kicks"),
    ("MGMT", "Electric Feel"), ("MGMT", "Kids"),
    ("Vance Joy", "Riptide"), ("The Lumineers", "Ho Hey"),
    ("Mumford & Sons", "I Will Wait"), ("Mumford & Sons", "Little Lion Man"),
    ("Bastille", "Pompeii"), ("Arctic Monkeys", "Do I Wanna Know?"), ("Arctic Monkeys", "R U Mine?"),
    ("The 1975", "Chocolate"), ("The 1975", "Somebody Else"),
    ("Hozier", "Take Me to Church"),
    ("Florence + The Machine", "Dog Days Are Over"), ("Florence + The Machine", "Shake It Out"),
    ("OneRepublic", "Counting Stars"), ("Maroon 5", "Payphone"), ("Maroon 5", "One More Night"),
    ("Train", "Hey, Soul Sister"), ("fun.", "We Are Young"), ("fun.", "Some Nights"),
    ("Ellie Goulding", "Love Me Like You Do"), ("Ellie Goulding", "Lights"),
    ("Jessie J", "Price Tag"), ("Jessie J", "Domino"), ("Little Mix", "Black Magic"),
    ("P!nk", "Just Give Me a Reason"), ("P!nk", "Try"),
    ("Christina Perri", "Jar of Hearts"), ("Gotye", "Somebody That I Used to Know"),
    ("Clean Bandit", "Rather Be"), ("AWOLNATION", "Sail"),
    ("American Authors", "Best Day of My Life"), ("X Ambassadors", "Renegades"),
    ("Alessia Cara", "Here"), ("Alessia Cara", "Scars to Your Beautiful"),
    ("Rachel Platten", "Fight Song"), ("Meghan Trainor", "Lips Are Movin"),
    ("Silento", "Watch Me (Whip/Nae Nae)"), ("OMI", "Cheerleader"), ("MAGIC!", "Rude"),
    ("Iggy Azalea", "Fancy"), ("Jason Derulo", "Talk Dirty"), ("Jason Derulo", "Want to Want Me"),
    ("Nick Jonas", "Jealous"), ("Fetty Wap", "Trap Queen"), ("Portugal. The Man", "Feel It Still"),
    ("Lauv", "I Like Me Better"), ("Julia Michaels", "Issues"), ("Niall Horan", "Slow Hands"),
    ("Anne-Marie", "2002"), ("James Bay", "Let It Go"),
    ("George Ezra", "Shotgun"), ("George Ezra", "Budapest"),
    ("Rag'n'Bone Man", "Human"), ("Milky Chance", "Stolen Dance"),
    ("Passenger", "Let Her Go"), ("Kodaline", "All I Want"),
    ("Of Monsters and Men", "Little Talks"), ("Lewis Capaldi", "Someone You Loved"),
]

SEED_SONGS_2020S = [
    ("Olivia Rodrigo", "Drivers License"), ("Olivia Rodrigo", "Good 4 U"),
    ("Harry Styles", "Watermelon Sugar"), ("Harry Styles", "As It Was"),
    ("The Kid LAROI", "Stay"), ("The Kid LAROI", "Without You"),
    ("Lil Nas X", "Old Town Road"), ("Lil Nas X", "Montero"),
    ("Doja Cat", "Say So"), ("Doja Cat", "Kiss Me More"), ("Doja Cat", "Woman"),
    ("Glass Animals", "Heat Waves"),
    ("Dua Lipa", "Levitating"), ("SZA", "Kill Bill"), ("Miley Cyrus", "Flowers"),
    ("Taylor Swift", "Anti-Hero"), ("Taylor Swift", "Cruel Summer"),
    ("Chappell Roan", "Good Luck, Babe!"), ("Sabrina Carpenter", "Espresso"),
    ("Benson Boone", "Beautiful Things"),
    ("Adele", "Easy On Me"), ("Ariana Grande", "Positions"),
    ("Megan Thee Stallion", "Savage"), ("Travis Scott", "Sicko Mode"),
    ("Kendrick Lamar", "HUMBLE."), ("Kendrick Lamar", "Not Like Us"),
    ("Tate McRae", "Greedy"), ("Ice Spice", "Munch"),
    ("Gracie Abrams", "That's So True"), ("Teddy Swims", "Lose Control"),
    ("Noah Kahan", "Stick Season"), ("Djo", "End of Beginning"),
    ("Billie Eilish", "Happier Than Ever"), ("Billie Eilish", "Birds of a Feather"),
    ("Billie Eilish", "What Was I Made For?"),
    ("The Weeknd", "Save Your Tears"), ("Dua Lipa", "Houdini"),
    ("Sabrina Carpenter", "Please Please Please"), ("Sabrina Carpenter", "Feather"),
    ("Sabrina Carpenter", "Taste"), ("Sabrina Carpenter", "Manchild"),
    ("Taylor Swift", "Lavender Haze"), ("Taylor Swift", "Karma"),
    ("Taylor Swift", "Fortnight"), ("Taylor Swift", "August"),
    ("Olivia Rodrigo", "Vampire"), ("Olivia Rodrigo", "Bad Idea Right?"),
    ("Ariana Grande", "We Can't Be Friends"), ("Ariana Grande", "Yes, And?"),
    ("Beyoncé", "Texas Hold 'Em"), ("Beyoncé", "Break My Soul"),
    ("Lady Gaga", "Die With A Smile"),
    ("SZA", "Snooze"), ("SZA", "Good Days"),
    ("Doja Cat", "Paint The Town Red"), ("Doja Cat", "Agora Hills"),
    ("Ice Spice", "Boy's a Liar Pt. 2"),
    ("Charli XCX", "Von Dutch"), ("Charli XCX", "Apple"), ("Charli XCX", "360"),
    ("Gracie Abrams", "I Love You, I'm Sorry"), ("Benson Boone", "Slow It Down"),
    ("Zach Bryan", "I Remember Everything"),
    ("Morgan Wallen", "Last Night"), ("Morgan Wallen", "You Proof"),
    ("Shaboozey", "A Bar Song (Tipsy)"), ("Jelly Roll", "Need a Favor"),
    ("Tyla", "Water"), ("Rema", "Calm Down"), ("Peso Pluma", "Ella Baila Sola"),
    ("Karol G", "TQG"), ("Shakira", "Bzrp Music Sessions, Vol. 53"),
    ("Miley Cyrus", "Used To Be Young"), ("Lana Del Rey", "A&W"),
    ("Reneé Rapp", "Snow Angel"), ("Hozier", "Too Sweet"),
    ("Chappell Roan", "Pink Pony Club"), ("Chappell Roan", "Hot To Go!"),
    ("Chappell Roan", "Red Wine Supernova"),
    ("Sombr", "Back to Friends"), ("Alex Warren", "Ordinary"),
    ("Post Malone", "I Had Some Help"),
    ("Role Model", "Sally, When The Wine Runs Out"),
    ("Myles Smith", "Stargazing"), ("Artemas", "i like the way you kiss me"),
    ("Kendrick Lamar", "Luther"), ("Addison Rae", "Diet Pepsi"),
    ("Justin Bieber", "Yummy"), ("Justin Bieber", "Peaches"), ("Justin Bieber", "Ghost"),
    ("Dua Lipa", "Physical"), ("Dua Lipa", "Break My Heart"),
    ("Miley Cyrus", "Midnight Sky"), ("Doja Cat", "Streets"), ("Doja Cat", "Vegas"),
    ("The Weeknd", "Heartless"), ("The Weeknd", "Take My Breath"), ("The Weeknd", "In Your Eyes"),
    ("Bad Bunny", "Titi Me Pregunto"), ("Bad Bunny", "Me Porto Bonito"),
    ("Bad Bunny", "Un Verano Sin Ti"), ("Bad Bunny", "Monaco"),
    ("Rosalía", "Despechá"), ("Rosalía", "Con Altura"),
    ("Karol G", "Provenza"), ("Karol G", "Mi Ex Tenía Razón"), ("Peso Pluma", "PRC"),
    ("Harry Styles", "Golden"), ("Harry Styles", "Adore You"), ("Harry Styles", "Late Night Talking"),
    ("Olivia Rodrigo", "Deja Vu"), ("Olivia Rodrigo", "Get Him Back!"),
    ("Sabrina Carpenter", "Nonsense"), ("Sabrina Carpenter", "Bed Chem"),
    ("Gracie Abrams", "Us."), ("Noah Kahan", "Dial Drunk"),
    ("Zach Bryan", "Something in the Orange"),
    ("Morgan Wallen", "Whiskey Glasses"), ("Morgan Wallen", "Wasted On You"), ("Morgan Wallen", "Cowgirls"),
    ("Lainey Wilson", "Watermelon Moonshine"), ("Lainey Wilson", "Heart Like a Truck"),
    ("Bailey Zimmerman", "Rock and a Hard Place"), ("Jelly Roll", "Save Me"),
    ("Luke Combs", "Fast Car"), ("HARDY", "wait in the truck"), ("Kane Brown", "One Mississippi"),
    ("BTS", "Dynamite"), ("BTS", "Butter"), ("BTS", "Permission to Dance"),
    ("Jung Kook", "Seven"), ("Jung Kook", "Standing Next to You"),
    ("NewJeans", "Super Shy"), ("NewJeans", "Attention"), ("NewJeans", "Hype Boy"),
    ("LE SSERAFIM", "Perfect Night"), ("TWICE", "The Feels"), ("FIFTY FIFTY", "Cupid"),
    ("Burna Boy", "Last Last"), ("Central Cee", "Doja"),
    ("GloRilla", "F.N.F. (Let's Go)"), ("Latto", "Big Energy"),
    ("Lil Nas X", "Industry Baby"), ("Lil Nas X", "That's What I Want"),
    ("Jack Harlow", "Lovin On Me"), ("GAYLE", "abcdefu"), ("Em Beihold", "Numb Little Bug"),
    ("Steve Lacy", "Bad Habit"), ("Omar Apollo", "Evergreen"), ("Beabadoobee", "Glue Song"),
    ("Wet Leg", "Chaise Longue"), ("The Backseat Lovers", "Kilby Girl"),
    ("Mitski", "My Love Mine All Mine"), ("Boygenius", "Not Strong Enough"),
    ("Fred again..", "Delilah (pull me out of this)"), ("JVKE", "golden hour"),
    ("David Kushner", "Daylight"),
    ("Tate McRae", "exes"), ("Tate McRae", "you broke me first"),
    ("Reneé Rapp", "Not My Fault"), ("Chappell Roan", "Casual"),
    ("Katseye", "Gnarly"), ("Katseye", "Touch"),
    ("Rauw Alejandro", "Todo de Ti"), ("Feid", "Classy 101"),
    ("Manuel Turizo", "La Bachata"), ("Grupo Frontera", "un x100to"),
    ("Kali Uchis", "Moonlight"), ("Kali Uchis", "telepatía"),
    ("FloyyMenor", "Gata Only"), ("Xavi", "La Diabla"),
]

DECADE_WEIGHTS = {
    "1960s-70s": 0.4,
    "1980s": 0.5,
    "1990s": 0.7,
    "2000s": 1.0,
    "2010s": 1.7,
    "2020s": 1.9,
}

SEED_SONGS = (
    [(a, t, "1960s-70s") for a, t in SEED_SONGS_60S_70S]
    + [(a, t, "1980s") for a, t in SEED_SONGS_80S]
    + [(a, t, "1990s") for a, t in SEED_SONGS_90S]
    + [(a, t, "2000s") for a, t in SEED_SONGS_2000S]
    + [(a, t, "2010s") for a, t in SEED_SONGS_2010S]
    + [(a, t, "2020s") for a, t in SEED_SONGS_2020S]
)


def _load():
    if not DATA_PATH.exists():
        return {}
    return json.loads(DATA_PATH.read_text())


def _save(data):
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(data, indent=2))


def _resolve(artist, title):
    matches = deezer.search_titles(f"{artist} {title}", limit=1)
    cover = matches[0]["cover"] if matches else ""
    video_id = youtube.video_id_for_track(f"{artist}::{title}", artist, title)
    return video_id, cover


def _sync_seed_songs(data):
    changed = False
    for artist, title, decade in SEED_SONGS:
        key = f"{artist}::{title}"
        if key not in data:
            data[key] = {
                "id": key,
                "artist": artist,
                "title": title,
                "decade": decade,
                "video_id": None,
                "cover": "",
                "resolved": False,
                "removed": False,
            }
            changed = True
        elif "decade" not in data[key]:
            data[key]["decade"] = decade  # backfill for entries saved before decades existed
            changed = True
    return changed


def _resolve_batch_in_background():
    global _resolution_running
    try:
        data = _load()
        # Resolve higher-weighted (more recent) decades first, so the
        # playable pool skews recent immediately instead of only after every
        # older decade in list order has already been resolved.
        unresolved = [e for e in data.values() if not e["resolved"]]
        unresolved.sort(key=lambda e: -DECADE_WEIGHTS.get(e.get("decade"), 1.0))

        resolved_this_call = 0
        changed = False
        for entry in unresolved:
            if resolved_this_call >= MAX_RESOLUTIONS_PER_CALL:
                break
            try:
                video_id, cover = _resolve(entry["artist"], entry["title"])
            except youtube.YouTubeError:
                break
            entry["video_id"] = video_id
            entry["cover"] = cover
            entry["resolved"] = True
            changed = True
            resolved_this_call += 1

        if changed:
            _save(data)
    finally:
        with _resolution_lock:
            _resolution_running = False


def get_all_songs():
    global _resolution_running
    data = _load()
    if _sync_seed_songs(data):
        _save(data)

    # Resolving costs YouTube search quota and real network time, so it must
    # never block a request that's just trying to start/load a round — kick
    # it off in the background (at most one run at a time) and return
    # immediately with whatever's already resolved. Each call nudges the pool
    # a little further along without anyone ever waiting on it.
    with _resolution_lock:
        if not _resolution_running and any(not e["resolved"] for e in data.values()):
            _resolution_running = True
            threading.Thread(target=_resolve_batch_in_background, daemon=True).start()

    return sorted(data.values(), key=lambda e: (e["artist"], e["title"]))


def random_playable_song():
    songs = [s for s in get_all_songs() if s["video_id"] and not s.get("removed")]
    weights = [DECADE_WEIGHTS.get(s.get("decade"), 1.0) for s in songs]
    return random.choices(songs, weights=weights, k=1)[0]


def remove_song(song_id):
    data = _load()
    if song_id not in data:
        raise KeyError(song_id)
    data[song_id]["removed"] = True
    _save(data)


def retry_video(song_id):
    data = _load()
    if song_id not in data:
        raise KeyError(song_id)
    entry = data[song_id]
    new_video_id = youtube.retry_video_id(song_id, entry["artist"], entry["title"], entry["video_id"])
    if new_video_id:
        entry["video_id"] = new_video_id
        _save(data)
    return entry
