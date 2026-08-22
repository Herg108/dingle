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
    ("Queen", "Bohemian Rhapsody"), ("Queen", "We Will Rock You"),
    ("Queen", "We Are the Champions"), ("Led Zeppelin", "Stairway to Heaven"),
    ("Eagles", "Hotel California"), ("Fleetwood Mac", "Dreams"),
    ("Fleetwood Mac", "Go Your Own Way"), ("Stevie Wonder", "Superstition"),
    ("Elton John", "Rocket Man"), ("Elton John", "Your Song"),
    ("David Bowie", "Heroes"), ("David Bowie", "Space Oddity"),
    ("ABBA", "Dancing Queen"), ("Bee Gees", "Stayin' Alive"),
    ("Earth, Wind & Fire", "September"), ("Bill Withers", "Ain't No Sunshine"),
    ("Bill Withers", "Lean on Me"), ("Billy Joel", "Piano Man"),
    ("The Jackson 5", "I Want You Back"), ("Donna Summer", "I Feel Love"),
    ("KC and the Sunshine Band", "Get Down Tonight"), ("The Beatles", "Hey Jude"),
    ("The Beatles", "Let It Be"), ("The Beatles", "Here Comes the Sun"),
    ("The Rolling Stones", "(I Can't Get No) Satisfaction"), ("The Beach Boys", "Good Vibrations"),
    ("Aretha Franklin", "Respect"), ("Otis Redding", "(Sittin' On) The Dock of the Bay"),
    ("The Supremes", "You Can't Hurry Love"), ("Marvin Gaye", "I Heard It Through the Grapevine"),
    ("Simon & Garfunkel", "The Sound of Silence"), ("Bob Dylan", "Like a Rolling Stone"),
    ("Elvis Presley", "Jailhouse Rock"), ("Chuck Berry", "Johnny B. Goode"),
    ("Bob Dylan", "Knockin' On Heaven's Door"), ("Frankie Valli", "Can't Take My Eyes off You"),
    ("The Ronettes", "Be My Baby"), ("Frank Sinatra", "My Way"),
    ("Bill Withers", "Lovely Day"), ("Paul Anka", "Put Your Head On My Shoulder"),
    ("AC/DC", "Highway to Hell"), ("Michael Jackson", "Rock with You"),
    ("Michael Jackson", "Don't Stop 'Til You Get Enough"), ("TOTO", "Hold the Line"),
    ("Elton John", "Goodbye Yellow Brick Road"), ("Bee Gees", "How Deep Is Your Love"),
    ("Bee Gees", "More Than A Woman"), ("ABBA", "Gimme! Gimme! Gimme! (A Man After Midnight)"),
    ("ABBA", "Mamma Mia"), ("ABBA", "Waterloo"),
    ("ABBA", "Money, Money, Money"), ("Bonnie Tyler", "It's a Heartache"),
    ("Blue Swede", "Hooked On A Feeling"), ("KISS", "I Was Made For Lovin' You"),
    ("Elton John", "Don't Go Breaking My Heart"), ("Neil Diamond", "Sweet Caroline"),
    ("The Beatles", "Twist And Shout"), ("Boston", "More Than a Feeling"),
    ("Lynyrd Skynyrd", "Sweet Home Alabama"), ("Lynyrd Skynyrd", "Free Bird"),
    ("Don McLean", "American Pie"), ("Village People", "Y.M.C.A."),
    ("Queen", "Don't Stop Me Now"), ("Queen", "Killer Queen"),
    ("Electric Light Orchestra", "Mr. Blue Sky"), ("Redbone", "Come and Get Your Love"),
    ("Earth, Wind & Fire", "Boogie Wonderland"), ("King Harvest", "Dancing in the Moonlight"),
    ("Badfinger", "Baby Blue"), ("Steve Miller Band", "The Joker"),
    ("The Cars", "Just What I Needed"), ("Blondie", "Heart of Glass"),
    ("Chic", "Le Freak"), ("Christopher Cross", "Sailing"),
    ("Player", "Baby Come Back"), ("Ambrosia", "Biggest Part of Me"),
    ("John Denver", "Take Me Home, Country Roads"),
]

SEED_SONGS_80S = [
    ("Michael Jackson", "Billie Jean"), ("Michael Jackson", "Thriller"),
    ("Michael Jackson", "Beat It"), ("Whitney Houston", "I Wanna Dance with Somebody"),
    ("Whitney Houston", "How Will I Know"), ("Madonna", "Like a Virgin"),
    ("Madonna", "Material Girl"), ("Prince", "Purple Rain"),
    ("Prince", "When Doves Cry"), ("a-ha", "Take On Me"),
    ("Journey", "Don't Stop Believin'"), ("Guns N' Roses", "Sweet Child O' Mine"),
    ("Bon Jovi", "Livin' on a Prayer"), ("Cyndi Lauper", "Girls Just Want to Have Fun"),
    ("Tears for Fears", "Everybody Wants to Rule the World"), ("Duran Duran", "Hungry Like the Wolf"),
    ("The Police", "Every Breath You Take"), ("Toto", "Africa"),
    ("Eurythmics", "Sweet Dreams (Are Made of This)"), ("Van Halen", "Jump"),
    ("Def Leppard", "Pour Some Sugar on Me"), ("INXS", "Never Tear Us Apart"),
    ("George Michael", "Faith"), ("Wham!", "Wake Me Up Before You Go-Go"),
    ("Phil Collins", "In the Air Tonight"), ("Crowded House", "Don't Dream It's Over"),
    ("The Smiths", "There Is a Light That Never Goes Out"), ("Grover Washington Jr.", "Just the Two of Us"),
    ("U2", "With Or Without You"), ("The Outfield", "Your Love"),
    ("Cutting Crew", "(I Just) Died In Your Arms"), ("Fleetwood Mac", "Everywhere"),
    ("Billy Idol", "Eyes Without A Face"), ("Eddie Money", "Take Me Home Tonight"),
    ("Men At Work", "Down Under"), ("Men At Work", "Who Can It Be Now?"),
    ("Tears For Fears", "Head Over Heels"), ("Journey", "Any Way You Want It"),
    ("AC/DC", "Back In Black"), ("AC/DC", "You Shook Me All Night Long"),
    ("Michael Jackson", "Smooth Criminal"), ("Guns N' Roses", "Welcome To The Jungle"),
    ("Bon Jovi", "You Give Love A Bad Name"), ("Elton John", "I'm Still Standing"),
    ("Eurythmics", "Here Comes the Rain Again"), ("Wham!", "Last Christmas"),
    ("ABBA", "Lay All Your Love On Me"), ("Rick Astley", "Never Gonna Give You Up"),
    ("Billy Joel", "Uptown Girl"), ("Billy Joel", "We Didn't Start the Fire"),
    ("Culture Club", "Karma Chameleon"), ("Europe", "The Final Countdown"),
    ("Survivor", "Eye of the Tiger"), ("Bonnie Tyler", "Total Eclipse of the Heart"),
    ("U2", "I Still Haven't Found What I'm Looking For"), ("Katrina & The Waves", "Walking On Sunshine"),
    ("The Proclaimers", "I'm Gonna Be (500 Miles)"), ("Bryan Adams", "Summer Of '69"),
    ("Joan Jett & the Blackhearts", "I Love Rock 'N Roll"), ("Roxette", "Listen To Your Heart"),
    ("Lipps Inc.", "Funkytown"), ("Queen", "Under Pressure"),
    ("Queen", "Another One Bites The Dust"), ("The Clash", "Should I Stay or Should I Go"),
    ("Alphaville", "Forever Young"), ("Tom Petty", "Free Fallin'"),
    ("Rick Springfield", "Jessie's Girl"), ("Foreigner", "I Want to Know What Love Is"),
    ("Journey", "Faithfully"), ("Toto", "Rosanna"),
    ("Whitesnake", "Here I Go Again"), ("Bon Jovi", "Wanted Dead or Alive"),
    ("Talking Heads", "Once in a Lifetime"), ("Devo", "Whip It"),
    ("Simple Minds", "Don't You (Forget About Me)"), ("Peter Gabriel", "Sledgehammer"),
    ("Genesis", "Invisible Touch"), ("Steve Winwood", "Higher Love"),
    ("Huey Lewis and the News", "The Power of Love"), ("Kool & The Gang", "Celebration"),
    ("Toni Basil", "Mickey"), ("Dexys Midnight Runners", "Come On Eileen"),
    ("Berlin", "Take My Breath Away"), ("Chicago", "You're the Inspiration"),
    ("Foreigner", "Waiting for a Girl Like You"), ("Air Supply", "All Out of Love"),
]

SEED_SONGS_90S = [
    ("Nirvana", "Smells Like Teen Spirit"), ("Whitney Houston", "I Will Always Love You"),
    ("Mariah Carey", "All I Want for Christmas Is You"), ("TLC", "No Scrubs"),
    ("TLC", "Waterfalls"), ("Backstreet Boys", "I Want It That Way"),
    ("*NSYNC", "Bye Bye Bye"), ("Britney Spears", "...Baby One More Time"),
    ("Spice Girls", "Wannabe"), ("Alanis Morissette", "Ironic"),
    ("Oasis", "Wonderwall"), ("Radiohead", "Creep"),
    ("Green Day", "Basket Case"), ("Red Hot Chili Peppers", "Under the Bridge"),
    ("R.E.M.", "Losing My Religion"), ("Toni Braxton", "Un-Break My Heart"),
    ("Boyz II Men", "End of the Road"), ("Celine Dion", "My Heart Will Go On"),
    ("The Notorious B.I.G.", "Juicy"), ("2Pac", "California Love"),
    ("Dr. Dre", "Nuthin' but a 'G' Thang"), ("Coolio", "Gangsta's Paradise"),
    ("Beastie Boys", "Sabotage"), ("No Doubt", "Don't Speak"),
    ("Sublime", "Santeria"), ("Smash Mouth", "All Star"),
    ("Run-D.M.C.", "Walk This Way"), ("Salt-N-Pepa", "Push It"),
    ("The Cranberries", "Linger"), ("Sixpence None The Richer", "Kiss Me"),
    ("Mazzy Star", "Fade Into You"), ("Spin Doctors", "Two Princes"),
    ("Aerosmith", "I Don't Want To Miss A Thing"), ("The Goo Goo Dolls", "Iris"),
    ("Tal Bachman", "She's so High"), ("Oasis", "Don't Look Back In Anger"),
    ("AC/DC", "Thunderstruck"), ("Haddaway", "What Is Love"),
    ("Fools Garden", "Lemon Tree"), ("Smash Mouth", "Walkin' On The Sun"),
    ("4 Non Blondes", "What's Up?"), ("Green Day", "Good Riddance (Time of Your Life)"),
    ("Ace of Base", "The Sign"), ("Cher", "Believe"),
    ("Backstreet Boys", "As Long as You Love Me"), ("Backstreet Boys", "Everybody (Backstreet's Back)"),
    ("Daft Punk", "One More Time"), ("Sugar Ray", "Fly"),
    ("New Radicals", "You Get What You Give"), ("Semisonic", "Closing Time"),
    ("Everlast", "What It's Like"), ("Creed", "Higher"),
    ("Third Eye Blind", "Semi-Charmed Life"), ("311", "Amber"),
    ("Blind Melon", "No Rain"), ("Oasis", "Champagne Supernova"),
    ("Weezer", "Buddy Holly"), ("Weezer", "Say It Ain't So"),
    ("Blur", "Song 2"), ("Pulp", "Common People"),
    ("Garbage", "Only Happy When It Rains"), ("Fastball", "The Way"),
    ("Marcy Playground", "Sex and Candy"), ("Eagle-Eye Cherry", "Save Tonight"),
    ("Savage Garden", "Truly Madly Deeply"), ("Savage Garden", "I Want You"),
    ("Aqua", "Barbie Girl"), ("Divinyls", "I Touch Myself"),
    ("Alanis Morissette", "You Oughta Know"), ("Meredith Brooks", "Bitch"),
    ("Natalie Imbruglia", "Torn"), ("Des'ree", "You Gotta Be"),
    ("En Vogue", "Don't Let Go (Love)"), ("SWV", "Weak"),
    ("Montell Jordan", "This Is How We Do It"), ("Next", "Too Close"),
    ("Deborah Cox", "Nobody's Supposed to Be Here"),
    ("Los Del Rio", "Macarena"),
]

SEED_SONGS_2000S = [
    ("Beyoncé", "Crazy in Love"), ("Beyoncé", "Single Ladies (Put a Ring on It)"),
    ("Outkast", "Hey Ya!"), ("Usher", "Yeah!"),
    ("Eminem", "Lose Yourself"), ("Eminem", "Without Me"),
    ("Kelly Clarkson", "Since U Been Gone"), ("Avril Lavigne", "Complicated"),
    ("Christina Aguilera", "Beautiful"), ("Justin Timberlake", "Cry Me a River"),
    ("Rihanna", "Umbrella"), ("Amy Winehouse", "Rehab"),
    ("Coldplay", "Yellow"), ("Coldplay", "Clocks"),
    ("Green Day", "Boulevard of Broken Dreams"), ("Linkin Park", "In the End"),
    ("Evanescence", "Bring Me to Life"), ("Fall Out Boy", "Sugar, We're Goin Down"),
    ("Panic! At The Disco", "I Write Sins Not Tragedies"), ("Kanye West", "Stronger"),
    ("Black Eyed Peas", "I Gotta Feeling"), ("Lady Gaga", "Poker Face"),
    ("Lady Gaga", "Bad Romance"), ("Katy Perry", "Firework"),
    ("Katy Perry", "Teenage Dream"), ("Taylor Swift", "Love Story"),
    ("Adele", "Rolling in the Deep"), ("Missy Elliott", "Get Ur Freak On"),
    ("Destiny's Child", "Say My Name"), ("Alicia Keys", "No One"),
    ("John Legend", "All of Me"), ("Coldplay", "Sparks"),
    ("Hoobastank", "The Reason"), ("Dido", "Thank You"),
    ("Modjo", "Lady (Hear Me Tonight)"), ("Outkast", "Ms. Jackson"),
    ("Iyaz", "Replay"), ("Coldplay", "Viva La Vida"),
    ("Bon Jovi", "It's My Life"), ("Smash Mouth", "I'm A Believer"),
    ("U2", "Beautiful Day"), ("Jason Mraz", "I'm Yours"),
    ("Kanye West", "I Wonder"), ("Kanye West", "Flashing Lights"),
    ("Owl City", "Fireflies"), ("Jason Derulo", "Whatcha Say"),
    ("Maroon 5", "This Love"), ("Colbie Caillat", "Bubbly"),
    ("Plain White T's", "Hey There Delilah"), ("Daniel Powter", "Bad Day"),
    ("Gorillaz", "Feel Good Inc."), ("Green Day", "Wake Me up When September Ends"),
    ("CeeLo Green", "Kung Fu Fighting"), ("Fergie", "Big Girls Don't Cry"),
    ("Keane", "Somewhere Only We Know"), ("Lady Gaga", "Just Dance"),
    ("Lady Gaga", "Paparazzi"), ("The All-American Rejects", "Gives You Hell"),
    ("Katy Perry", "Hot N Cold"), ("Katy Perry", "I Kissed A Girl"),
    ("Justin Timberlake", "Rock Your Body"), ("OneRepublic", "Secrets"),
    ("OneRepublic", "Apologize"), ("OneRepublic", "Stop And Stare"),
    ("Train", "Drops of Jupiter (Tell Me)"), ("Rihanna", "Don't Stop The Music"),
    ("Snow Patrol", "Chasing Cars"), ("The Killers", "Mr. Brightside"),
    ("The Killers", "Somebody Told Me"), ("The All-American Rejects", "Dirty Little Secret"),
    ("Caesars", "Jerk It Out"), ("Red Hot Chili Peppers", "Can't Stop"),
    ("Red Hot Chili Peppers", "Otherside"), ("Red Hot Chili Peppers", "Dani California"),
    ("Red Hot Chili Peppers", "Snow (Hey Oh)"), ("Gwen Stefani", "The Sweet Escape"),
    ("Gwen Stefani", "Hollaback Girl"), ("Akon", "Smack That"),
    ("Flo Rida", "Right Round"), ("Maroon 5", "She Will Be Loved"),
    ("Maroon 5", "Sunday Morning"), ("Miley Cyrus", "Party In The U.S.A."),
    ("Vanessa Carlton", "A Thousand Miles"), ("The Script", "Breakeven"),
    ("The Script", "The Man Who Can't Be Moved"), ("Alicia Keys", "If I Ain't Got You"),
    ("Alicia Keys", "Fallin'"), ("The Fray", "How to Save a Life"),
    ("Empire Of The Sun", "Walking On A Dream"), ("The Fray", "You Found Me"),
    ("Empire Of The Sun", "We Are The People"), ("Kid Cudi", "Day 'N' Nite"),
    ("Nelly Furtado", "Say It Right"), ("Sheryl Crow", "Soak Up The Sun"),
    ("Gnarls Barkley", "Crazy"), ("Natasha Bedingfield", "Unwritten"),
    ("Kings of Leon", "Use Somebody"), ("No Doubt", "Hella Good"),
    ("Natasha Bedingfield", "Pocketful of Sunshine"), ("Sara Bareilles", "Love Song"),
    ("Maroon 5", "Won't Go Home Without You"), ("JAY-Z", "Empire State Of Mind"),
    ("Estelle", "American Boy"), ("Justin Timberlake", "SexyBack"),
    ("Timbaland", "The Way I Are"), ("KT Tunstall", "Suddenly I See"),
    ("Matchbox Twenty", "Unwell"), ("Uncle Kracker", "Drift Away"),
    ("3 Doors Down", "Here Without You"), ("Lifehouse", "You And Me"),
    ("Nelly Furtado", "I'm Like A Bird"), ("Sisqo", "Thong Song"),
    ("Usher", "Confessions Part II"), ("Usher", "U Got It Bad"),
    ("Ashanti", "Foolish"), ("Ciara", "1, 2 Step"),
    ("Ciara", "Goodies"), ("Mya", "My Love Is Like... Wo"),
    ("Good Charlotte", "Lifestyles of the Rich and Famous"), ("Simple Plan", "Welcome to My Life"),
    ("Sum 41", "In Too Deep"), ("Yellowcard", "Ocean Avenue"),
    ("My Chemical Romance", "Welcome to the Black Parade"), ("My Chemical Romance", "I'm Not Okay (I Promise)"),
    ("Paramore", "Misery Business"), ("The All-American Rejects", "Move Along"),
    ("Boys Like Girls", "The Great Escape"), ("Jimmy Eat World", "Sweetness"),
    ("Bon Iver", "Skinny Love"), ("Phoenix", "1901"),
    ("Carrie Underwood", "Before He Cheats"), ("Rascal Flatts", "Life is a Highway"),
]

SEED_SONGS_2010S = [
    ("Adele", "Someone Like You"), ("Adele", "Hello"),
    ("Bruno Mars", "Uptown Funk"), ("Bruno Mars", "Just the Way You Are"),
    ("Bruno Mars", "24K Magic"), ("Ed Sheeran", "Shape of You"),
    ("Ed Sheeran", "Perfect"), ("Ed Sheeran", "Thinking Out Loud"),
    ("Ed Sheeran", "Bad Habits"), ("Taylor Swift", "Shake It Off"),
    ("Taylor Swift", "Blank Space"), ("Katy Perry", "Roar"),
    ("Pharrell Williams", "Happy"), ("Daft Punk", "Get Lucky"),
    ("Imagine Dragons", "Radioactive"), ("Imagine Dragons", "Believer"),
    ("The Weeknd", "Can't Feel My Face"), ("The Weeknd", "Blinding Lights"),
    ("Sia", "Chandelier"), ("Rihanna", "Diamonds"),
    ("Rihanna", "Work"), ("Rihanna", "Needed Me"),
    ("Sam Smith", "Stay With Me"), ("Lorde", "Royals"),
    ("Meghan Trainor", "All About That Bass"), ("Justin Bieber", "Sorry"),
    ("Justin Bieber", "Baby"), ("Justin Bieber", "Love Yourself"),
    ("Miley Cyrus", "Wrecking Ball"), ("One Direction", "What Makes You Beautiful"),
    ("Carly Rae Jepsen", "Call Me Maybe"), ("Psy", "Gangnam Style"),
    ("Robin Thicke", "Blurred Lines"), ("Drake", "Hotline Bling"),
    ("Drake", "God's Plan"), ("Post Malone", "Circles"),
    ("Post Malone", "Sunflower"), ("Post Malone", "rockstar"),
    ("Dua Lipa", "New Rules"), ("Dua Lipa", "Don't Start Now"),
    ("Camila Cabello", "Havana"), ("Billie Eilish", "Bad Guy"),
    ("Billie Eilish", "Ocean Eyes"), ("Ariana Grande", "Thank U, Next"),
    ("Ariana Grande", "7 Rings"), ("Ariana Grande", "Problem"),
    ("Ariana Grande", "Into You"), ("Shawn Mendes", "Stitches"),
    ("Charlie Puth", "Attention"), ("Maroon 5", "Sugar"),
    ("Maroon 5", "Girls Like You"), ("The Chainsmokers", "Closer"),
    ("Zedd", "The Middle"), ("Marshmello", "Happier"),
    ("Halsey", "Without Me"), ("Khalid", "Location"),
    ("Cardi B", "Bodak Yellow"), ("Lizzo", "Truth Hurts"),
    ("Walk the Moon", "Shut Up and Dance"), ("Fifth Harmony", "Work from Home"),
    ("Zayn", "Pillowtalk"), ("Shawn Mendes", "Señorita"),
    ("Jonas Brothers", "Sucker"), ("24kGoldn", "Mood"),
    ("Jack Harlow", "First Class"), ("Lil Baby", "Drip Too Hard"),
    ("Roddy Ricch", "The Box"), ("Taylor Swift", "You Belong With Me"),
    ("Taylor Swift", "22"), ("Taylor Swift", "Bad Blood"),
    ("Taylor Swift", "Look What You Made Me Do"), ("Taylor Swift", "Delicate"),
    ("Taylor Swift", "Style"), ("Taylor Swift", "Wildest Dreams"),
    ("Taylor Swift", "I Knew You Were Trouble"), ("Ariana Grande", "No Tears Left To Cry"),
    ("Ariana Grande", "God Is a Woman"), ("Ariana Grande", "Side To Side"),
    ("Ariana Grande", "Dangerous Woman"), ("Ariana Grande", "Break Free"),
    ("Katy Perry", "Dark Horse"), ("Katy Perry", "California Gurls"),
    ("Katy Perry", "Wide Awake"), ("Katy Perry", "Part Of Me"),
    ("Selena Gomez", "Come & Get It"), ("Selena Gomez", "Same Old Love"),
    ("Selena Gomez", "Bad Liar"), ("Selena Gomez", "Wolves"),
    ("Camila Cabello", "Never Be the Same"), ("Shawn Mendes", "Treat You Better"),
    ("Shawn Mendes", "There's Nothing Holdin' Me Back"), ("Shawn Mendes", "In My Blood"),
    ("Shawn Mendes", "Mercy"), ("Halsey", "Bad At Love"),
    ("Halsey", "Him & I"), ("Halsey", "Colors"),
    ("Halsey", "Now or Never"), ("Demi Lovato", "Sorry Not Sorry"),
    ("Demi Lovato", "Confident"), ("Demi Lovato", "Skyscraper"),
    ("Demi Lovato", "Heart Attack"), ("Kesha", "Tik Tok"),
    ("Kesha", "Die Young"), ("Kesha", "Praying"),
    ("Pitbull", "Timber"), ("Pitbull", "Give Me Everything"),
    ("Pitbull", "International Love"), ("Flo Rida", "Whistle"),
    ("Flo Rida", "Good Feeling"), ("Flo Rida", "Low"),
    ("Britney Spears", "Till the World Ends"), ("Britney Spears", "Hold It Against Me"),
    ("Sia", "Cheap Thrills"), ("Sia", "Elastic Heart"),
    ("Sia", "Titanium"), ("Sam Smith", "I'm Not the Only One"),
    ("Sam Smith", "Too Good at Goodbyes"), ("Adele", "Set Fire to the Rain"),
    ("Ed Sheeran", "Photograph"), ("Ed Sheeran", "Castle on the Hill"),
    ("Ed Sheeran", "Galway Girl"), ("Justin Bieber", "What Do You Mean?"),
    ("Justin Bieber", "Company"), ("Charlie Puth", "See You Again"),
    ("Charlie Puth", "We Don't Talk Anymore"), ("Zedd", "Clarity"),
    ("Marshmello", "Alone"), ("Calvin Harris", "Summer"),
    ("Calvin Harris", "This Is What You Came For"), ("Calvin Harris", "Feel So Close"),
    ("Calvin Harris", "Outside"), ("David Guetta", "Play Hard"),
    ("Avicii", "Wake Me Up"), ("Avicii", "Levels"),
    ("Avicii", "Hey Brother"), ("Martin Garrix", "Animals"),
    ("Martin Garrix", "In the Name of Love"), ("Major Lazer", "Lean On"),
    ("DJ Snake", "Turn Down for What"), ("The Chainsmokers", "Don't Let Me Down"),
    ("The Chainsmokers", "Something Just Like This"), ("The Chainsmokers", "Paris"),
    ("Drake", "One Dance"), ("Drake", "In My Feelings"),
    ("Drake", "Started From the Bottom"), ("Drake", "Hold On, We're Going Home"),
    ("Kendrick Lamar", "Alright"), ("Kendrick Lamar", "Swimming Pools"),
    ("Kendrick Lamar", "King Kunta"), ("Travis Scott", "Goosebumps"),
    ("Travis Scott", "Antidote"), ("Future", "Mask Off"),
    ("Cardi B", "I Like It"), ("Cardi B", "Money"),
    ("Megan Thee Stallion", "Hot Girl Summer"), ("Nicki Minaj", "Anaconda"),
    ("Nicki Minaj", "Super Bass"), ("Migos", "Bad and Boujee"),
    ("J. Cole", "No Role Modelz"), ("Lizzo", "Good as Hell"),
    ("SZA", "Love Galore"), ("SZA", "The Weekend"),
    ("Khalid", "Young Dumb & Broke"), ("Khalid", "Talk"),
    ("The Weeknd", "Starboy"), ("The Weeknd", "The Hills"),
    ("The Weeknd", "Earned It"), ("Frank Ocean", "Thinking Bout You"),
    ("Frank Ocean", "Pink + White"), ("Bruno Mars", "Locked Out of Heaven"),
    ("Bruno Mars", "Grenade"), ("Bruno Mars", "Treasure"),
    ("Daniel Caesar", "Best Part"), ("BTS", "Boy With Luv"),
    ("BLACKPINK", "Kill This Love"), ("BLACKPINK", "DDU-DU DDU-DU"),
    ("Imagine Dragons", "Thunder"), ("Imagine Dragons", "Demons"),
    ("Imagine Dragons", "Whatever It Takes"), ("Twenty One Pilots", "Stressed Out"),
    ("Twenty One Pilots", "Ride"), ("Twenty One Pilots", "Heathens"),
    ("Panic! At The Disco", "High Hopes"), ("Fall Out Boy", "Centuries"),
    ("Fall Out Boy", "My Songs Know What You Did in the Dark"), ("Cage The Elephant", "Cigarette Daydreams"),
    ("Foster The People", "Pumped Up Kicks"), ("MGMT", "Electric Feel"),
    ("MGMT", "Kids"), ("Vance Joy", "Riptide"),
    ("The Lumineers", "Ho Hey"), ("Mumford & Sons", "I Will Wait"),
    ("Mumford & Sons", "Little Lion Man"), ("Bastille", "Pompeii"),
    ("Arctic Monkeys", "Do I Wanna Know?"), ("Arctic Monkeys", "R U Mine?"),
    ("The 1975", "Chocolate"), ("The 1975", "Somebody Else"),
    ("Hozier", "Take Me to Church"), ("Florence + The Machine", "Dog Days Are Over"),
    ("Florence + The Machine", "Shake It Out"), ("OneRepublic", "Counting Stars"),
    ("Maroon 5", "Payphone"), ("Maroon 5", "One More Night"),
    ("Train", "Hey, Soul Sister"), ("fun.", "We Are Young"),
    ("fun.", "Some Nights"), ("Ellie Goulding", "Love Me Like You Do"),
    ("Ellie Goulding", "Lights"), ("Jessie J", "Price Tag"),
    ("Jessie J", "Domino"), ("Little Mix", "Black Magic"),
    ("P!nk", "Just Give Me a Reason"), ("P!nk", "Try"),
    ("Christina Perri", "Jar of Hearts"), ("Gotye", "Somebody That I Used to Know"),
    ("Clean Bandit", "Rather Be"), ("AWOLNATION", "Sail"),
    ("American Authors", "Best Day of My Life"), ("X Ambassadors", "Renegades"),
    ("Alessia Cara", "Here"), ("Alessia Cara", "Scars to Your Beautiful"),
    ("Rachel Platten", "Fight Song"), ("Meghan Trainor", "Lips Are Movin"),
    ("Silento", "Watch Me (Whip/Nae Nae)"), ("OMI", "Cheerleader"),
    ("MAGIC!", "Rude"), ("Iggy Azalea", "Fancy"),
    ("Jason Derulo", "Talk Dirty"), ("Jason Derulo", "Want to Want Me"),
    ("Nick Jonas", "Jealous"), ("Fetty Wap", "Trap Queen"),
    ("Portugal. The Man", "Feel It Still"), ("Lauv", "I Like Me Better"),
    ("Julia Michaels", "Issues"), ("Niall Horan", "Slow Hands"),
    ("Anne-Marie", "2002"), ("James Bay", "Let It Go"),
    ("George Ezra", "Shotgun"), ("George Ezra", "Budapest"),
    ("Rag'n'Bone Man", "Human"), ("Milky Chance", "Stolen Dance"),
    ("Passenger", "Let Her Go"), ("Kodaline", "All I Want"),
    ("Of Monsters and Men", "Little Talks"), ("Lewis Capaldi", "Someone You Loved"),
    ("She & Him", "I Thought I Saw Your Face Today"), ("Cigarettes After Sex", "Apocalypse"),
    ("Rex Orange County", "THE SHADE"), ("TV Girl", "Lovers Rock"),
    ("Tame Impala", "The Less I Know The Better"), ("Fitz and The Tantrums", "Out of My League"),
    ("Coldplay", "A Sky Full of Stars"), ("Coldplay", "Hymn for the Weekend"),
    ("Coldplay", "Paradise"), ("Coldplay", "Adventure of a Lifetime"),
    ("Jason Mraz", "I Won't Give Up"), ("Echosmith", "Cool Kids"),
    ("Capital Cities", "Safe and Sound"), ("Migos", "Stir Fry"),
    ("Post Malone", "White Iverson"), ("The Weeknd", "Pray For Me"),
    ("The Weeknd", "I Feel It Coming"), ("The Neighbourhood", "Sweater Weather"),
    ("Kodak Black", "ZEZE"), ("The Weeknd", "Call Out My Name"),
    ("Lil Nas X", "Panini"), ("Khalid", "Better"),
    ("CKay", "love nwantiti (ah ah ah)"), ("Flo Rida", "My House"),
    ("Andy Grammer", "Keep Your Head Up"), ("Bruno Mars", "The Lazy Song"),
    ("Phillip Phillips", "Gone, Gone, Gone"), ("Gavin DeGraw", "Not Over You"),
    ("Pitbull", "Time of Our Lives"), ("Christina Perri", "a thousand years"),
    ("One Direction", "Story of My Life"), ("Hot Chelle Rae", "Tonight Tonight"),
    ("Imagine Dragons", "On Top Of The World"), ("Train", "Drive By"),
    ("The Wanted", "Glad You Came"), ("Owl City", "Good Time"),
    ("Travie McCoy", "Billionaire"), ("CeeLo Green", "Forget You"),
    ("Gym Class Heroes", "Stereo Hearts"), ("Rixton", "Me And My Broken Heart"),
    ("Andy Grammer", "Honey, I'm Good."), ("OneRepublic", "Good Life"),
    ("Bruno Mars", "Count on Me"), ("Neon Trees", "Everybody Talks"),
    ("Nico & Vinz", "Am I Wrong"), ("MKTO", "Classic"),
    ("Swedish House Mafia", "Don't You Worry Child"), ("Duck Sauce", "Barbra Streisand"),
    ("Kungs", "This Girl (Kungs Vs. Cookin' On 3 Burners)"), ("Sub Urban", "Cradles"),
    ("Bruno Mars", "When I Was Your Man"), ("Neon Trees", "Animal"),
    ("Jason Mraz", "Have It All"), ("Flo Rida", "Wild Ones"),
    ("Flo Rida", "GDFR"), ("LMFAO", "Party Rock Anthem"),
    ("LMFAO", "Sexy And I Know It"), ("Bruno Mars", "That's What I Like"),
    ("Bruno Mars", "Talking to the Moon"), ("Bruno Mars", "Marry You"),
    ("Bruno Mars", "It Will Rain"), ("B.o.B", "Nothin' on You"),
    ("Bruno Mars", "Finesse"), ("Lady Gaga", "Shallow"),
    ("Lady Gaga", "Telephone"), ("Lady Gaga", "The Edge Of Glory"),
    ("Lady Gaga", "Born This Way"), ("Lady Gaga", "Applause"),
    ("Lady Gaga", "Million Reasons"), ("The Weeknd", "Die For You"),
    ("Ariana Grande", "Love Me Harder"), ("The Weeknd", "Often"),
    ("Playboi Carti", "Magnolia"), ("Ariana Grande", "Santa Tell Me"),
    ("Ariana Grande", "One Last Time"), ("Ariana Grande", "break up with your girlfriend, i'm bored"),
    ("Ariana Grande", "breathin"), ("Jessie J", "Bang Bang"),
    ("Justin Bieber", "Beauty And A Beat"), ("DJ Snake", "Let Me Love You"),
    ("Major Lazer", "Cold Water"), ("DJ Khaled", "I'm the One"),
    ("Jack Ü", "Where Are Ü Now"), ("Ed Sheeran & Justin Bieber", "I Don't Care"),
    ("Ed Sheeran", "The A Team"), ("Ed Sheeran", "Beautiful People"),
    ("Ed Sheeran", "Don't"), ("Ed Sheeran", "South of the Border"),
    ("Billie Eilish", "lovely"), ("benny blanco", "Eastside"),
    ("Khalid", "Love Lies"), ("Rihanna", "We Found Love"),
    ("Calvin Harris", "One Kiss"), ("Calvin Harris", "Blame"),
    ("Calvin Harris", "Feels"), ("Calvin Harris", "Giant"),
    ("benny blanco", "I Found You"), ("Taylor Swift", "ME!"),
    ("Taylor Swift", "Lover"), ("Taylor Swift", "Don't Blame Me"),
    ("ZAYN", "I Don't Wanna Live Forever"), ("Taylor Swift", "You Need To Calm Down"),
    ("Taylor Swift", "We Are Never Ever Getting Back Together"), ("SHAED", "Trampoline"),
    ("Post Malone", "Congratulations"), ("Post Malone", "Better Now"),
    ("Post Malone", "Wow."), ("Post Malone", "Psycho"),
    ("Post Malone", "I Fall Apart"), ("Post Malone", "Goodbyes"),
    ("Wiz Khalifa", "The Thrill"), ("Wiz Khalifa", "Black and Yellow"),
    ("Charlie Puth", "One Call Away"), ("Charlie Puth", "How Long"),
    ("Charlie Puth", "Marvin Gaye"), ("Selena Gomez", "Good For You"),
    ("Kygo", "It Ain't Me"), ("Selena Gomez", "Lose You To Love Me"),
    ("Selena Gomez", "Back To You"), ("Selena Gomez & The Scene", "Love You Like A Love Song"),
    ("The Chainsmokers", "Roses"), ("The Chainsmokers", "This Feeling"),
    ("The Chainsmokers", "Call You Mine"), ("The Chainsmokers", "Who Do You Love"),
    ("Panic! At The Disco", "House of Memories"), ("fun.", "Carry On"),
    ("Foster The People", "Sit Next to Me"), ("Katy Perry", "Last Friday Night (T.G.I.F.)"),
    ("Katy Perry", "The One That Got Away"), ("Katy Perry", "E.T."),
    ("Katy Perry", "Never Really Over"), ("Justin Timberlake", "Mirrors"),
    ("Justin Timberlake", "CAN'T STOP THE FEELING!"), ("Justin Timberlake", "Say Something"),
    ("OneRepublic", "I Lived"), ("OneRepublic", "All The Right Moves"),
    ("OneRepublic", "Love Runs Out"), ("OneRepublic", "West Coast"),
    ("Shawn Mendes", "If I Can't Have You"), ("Shawn Mendes", "Lost In Japan"),
    ("Shawn Mendes", "I Know What You Did Last Summer"), ("DNCE", "Cake By The Ocean"),
    ("DNCE", "Toothbrush"), ("Rihanna", "Love On The Brain"),
    ("Rihanna", "Only Girl (In The World)"), ("Rihanna", "S&M"),
    ("Eminem", "Love The Way You Lie"), ("Eminem", "The Monster"),
    ("DJ Khaled", "No Brainer"), ("Kesha", "We R Who We R"),
    ("Kesha", "Blow"), ("Carly Rae Jepsen", "I Really Like You"),
    ("Kendrick Lamar", "All The Stars"), ("Taio Cruz", "Break Your Heart"),
    ("Maroon 5", "Maps"), ("Maroon 5", "Moves Like Jagger"),
    ("Imagine Dragons", "Natural"), ("Mark Ronson", "Nothing Breaks Like a Heart"),
    ("Sia", "Unstoppable"), ("Sia", "Snowman"),
    ("One Direction", "Night Changes"), ("One Direction", "Drag Me Down"),
    ("One Direction", "Best Song Ever"), ("Nicki Minaj", "Starships"),
    ("5 Seconds of Summer", "Youngblood"), ("Clean Bandit", "Symphony"),
    ("Clean Bandit", "Rockabye"), ("The Script", "Hall of Fame"),
    ("The Script", "Superheroes"), ("Macklemore", "Can't Hold Us"),
    ("Macklemore & Ryan Lewis", "Thrift Shop"), ("Macklemore", "Glorious"),
    ("Macklemore", "Good Old Days"), ("Maroon 5", "Cold"),
    ("USHER", "DJ Got Us Fallin' In Love"), ("Alicia Keys", "Girl on Fire"),
    ("Lorde", "Team"), ("Imagine Dragons", "It's Time"),
    ("Plain White T's", "Rhythm Of Love"), ("John Newman", "Love Me Again"),
    ("Tom Odell", "Another Love"), ("G-Eazy", "Me, Myself & I"),
    ("M83", "Midnight City"), ("R. City", "Locked Away"),
    ("Owl City", "When Can I See You Again?"), ("Pitbull", "Feel This Moment"),
    ("James Arthur", "Say You Won't Let Go"), ("Lil Mosey", "Noticed"),
    ("Gesaffelstein", "Lost in the Fire"), ("DJ Snake", "Middle"),
    ("KALEO", "Way down We Go"), ("Bazzi", "Fantasy"),
    ("Chris Brown", "No Guidance"), ("The Weeknd", "Reminder"),
    ("Marshmello", "Silence"), ("Jon Bellion", "All Time Low"),
    ("Why Don't We", "8 Letters"), ("XXXTENTACION", "SAD!"),
    ("Lana Del Rey", "Summertime Sadness"), ("The Weeknd", "In The Night"),
    ("Juice WRLD", "All Girls Are The Same"), ("Offset", "Ric Flair Drip"),
    ("Drake", "Jumpman"), ("Future", "Low Life"),
    ("Playboi Carti", "wokeuplikethis*"), ("Big Sean", "I Don't Fuck With You"),
    ("Juice WRLD", "Lucid Dreams"), ("Meek Mill", "Going Bad"),
    ("Miguel", "Sure Thing"), ("Tove Lo", "Habits (Stay High)"),
    ("Mike Posner", "I Took A Pill In Ibiza"), ("A$AP Rocky", "Praise The Lord (Da Shine)"),
    ("A Boogie Wit da Hoodie", "Drowning"), ("Disclosure", "Latch"),
    ("Drake", "Headlines"), ("Arctic Monkeys", "I Wanna Be Yours"),
    ("Kanye West", "Runaway"), ("Maroon 5", "Don't Wanna Know"),
    ("BORNS", "Electric Love"), ("Joji", "SLOW DANCING IN THE DARK"),
    ("Phillip Phillips", "Home"), ("Black Eyed Peas", "Just Can't Get Enough"),
    ("Charlie Puth", "Done for Me"), ("The Revivalists", "Wish I Knew You"),
    ("Colbie Caillat", "Brighter Than The Sun"), ("Fetty Wap", "679"),
    ("Lukas Graham", "7 Years"), ("Breakbot", "Baby I'm Yours"),
    ("Noisestorm", "Crab Rave"), ("Paramore", "Still Into You"),
    ("Alt-J", "Breezeblocks"), ("Grouplove", "Tongue Tied"),
    ("Lord Huron", "The Night We Met"), ("Two Door Cinema Club", "What You Know"),
    ("The Neighbourhood", "Daddy Issues"), ("Wolf Alice", "Don't Delete the Kisses"),
    ("Glass Animals", "Gooey"), ("Chvrches", "The Mother We Share"),
    ("BTS", "DNA"), ("SEVENTEEN", "Very Nice"),
    ("PSY", "Daddy"), ("Hozier", "Work Song"),
    ("Luis Fonsi", "Despacito"), ("Shakira", "Waka Waka (This Time for Africa)"),
    ("Playboi Carti", "Wok"), ("Travis Scott", "sdp interlude"),
    ("Travis Scott", "Don't Play"), ("Travis Scott", "5% TINT"),
    ("Travis Scott", "90210"), ("Travis Scott", "SKELETONS"),
    ("Travis Scott", "Nightcrawler"), ("Travis Scott", "Quintana Pt. 2"),
    ("Travis Scott", "STARGAZING"), ("Sheck Wes", "ILMB"),
    ("The Weeknd", "I Was Never There"), ("The Weeknd", "Secrets"),
    ("Kanye West", "Heartless"), ("Lil Uzi Vert", "20 Min"),
    ("Tyga", "Taste"),
]

SEED_SONGS_2020S = [
    ("Olivia Rodrigo", "Drivers License"), ("Olivia Rodrigo", "Good 4 U"),
    ("Harry Styles", "Watermelon Sugar"), ("Harry Styles", "As It Was"),
    ("The Kid LAROI", "Stay"), ("The Kid LAROI", "Without You"),
    ("Lil Nas X", "Old Town Road"), ("Lil Nas X", "Montero"),
    ("Doja Cat", "Say So"), ("Doja Cat", "Kiss Me More"),
    ("Doja Cat", "Woman"), ("Glass Animals", "Heat Waves"),
    ("Dua Lipa", "Levitating"), ("SZA", "Kill Bill"),
    ("Miley Cyrus", "Flowers"), ("Taylor Swift", "Anti-Hero"),
    ("Taylor Swift", "Cruel Summer"), ("Chappell Roan", "Good Luck, Babe!"),
    ("Sabrina Carpenter", "Espresso"), ("Benson Boone", "Beautiful Things"),
    ("Adele", "Easy On Me"), ("Ariana Grande", "Positions"),
    ("Megan Thee Stallion", "Savage"), ("Travis Scott", "Sicko Mode"),
    ("Kendrick Lamar", "HUMBLE."), ("Kendrick Lamar", "Not Like Us"),
    ("Tate McRae", "Greedy"), ("Ice Spice", "Munch"),
    ("Gracie Abrams", "That's So True"), ("Teddy Swims", "Lose Control"),
    ("Noah Kahan", "Stick Season"), ("Djo", "End of Beginning"),
    ("Billie Eilish", "Happier Than Ever"), ("Billie Eilish", "Birds of a Feather"),
    ("Billie Eilish", "What Was I Made For?"), ("The Weeknd", "Save Your Tears"),
    ("Dua Lipa", "Houdini"), ("Sabrina Carpenter", "Please Please Please"),
    ("Sabrina Carpenter", "Feather"), ("Sabrina Carpenter", "Taste"),
    ("Sabrina Carpenter", "Manchild"), ("Taylor Swift", "Lavender Haze"),
    ("Taylor Swift", "Karma"), ("Taylor Swift", "Fortnight"),
    ("Taylor Swift", "August"), ("Olivia Rodrigo", "Vampire"),
    ("Olivia Rodrigo", "Bad Idea Right?"), ("Ariana Grande", "We Can't Be Friends"),
    ("Ariana Grande", "Yes, And?"), ("Beyoncé", "Texas Hold 'Em"),
    ("Beyoncé", "Break My Soul"), ("Lady Gaga", "Die With A Smile"),
    ("SZA", "Snooze"), ("SZA", "Good Days"),
    ("Doja Cat", "Paint The Town Red"), ("Doja Cat", "Agora Hills"),
    ("Ice Spice", "Boy's a Liar Pt. 2"), ("Charli XCX", "Von Dutch"),
    ("Charli XCX", "Apple"), ("Charli XCX", "360"),
    ("Gracie Abrams", "I Love You, I'm Sorry"), ("Benson Boone", "Slow It Down"),
    ("Tyla", "Water"), ("Rema", "Calm Down"),
    ("Miley Cyrus", "Used To Be Young"), ("Lana Del Rey", "A&W"),
    ("Reneé Rapp", "Snow Angel"), ("Hozier", "Too Sweet"),
    ("Chappell Roan", "Pink Pony Club"), ("Chappell Roan", "Hot To Go!"),
    ("Chappell Roan", "Red Wine Supernova"), ("Sombr", "Back to Friends"),
    ("Alex Warren", "Ordinary"), ("Post Malone", "I Had Some Help"),
    ("Role Model", "Sally, When The Wine Runs Out"), ("Myles Smith", "Stargazing"),
    ("Artemas", "i like the way you kiss me"), ("Kendrick Lamar", "Luther"),
    ("Addison Rae", "Diet Pepsi"), ("Justin Bieber", "Yummy"),
    ("Justin Bieber", "Peaches"), ("Justin Bieber", "Ghost"),
    ("Dua Lipa", "Physical"), ("Dua Lipa", "Break My Heart"),
    ("Miley Cyrus", "Midnight Sky"), ("Doja Cat", "Streets"),
    ("Doja Cat", "Vegas"), ("The Weeknd", "Heartless"),
    ("The Weeknd", "Take My Breath"), ("The Weeknd", "In Your Eyes"),
    ("Harry Styles", "Golden"), ("Harry Styles", "Adore You"),
    ("Harry Styles", "Late Night Talking"), ("Olivia Rodrigo", "Deja Vu"),
    ("Olivia Rodrigo", "Get Him Back!"), ("Sabrina Carpenter", "Nonsense"),
    ("Sabrina Carpenter", "Bed Chem"), ("Gracie Abrams", "Us."),
    ("Noah Kahan", "Dial Drunk"), ("BTS", "Dynamite"),
    ("BTS", "Butter"), ("BTS", "Permission to Dance"),
    ("Jung Kook", "Seven"), ("Jung Kook", "Standing Next to You"),
    ("NewJeans", "Super Shy"), ("NewJeans", "Attention"),
    ("NewJeans", "Hype Boy"), ("LE SSERAFIM", "Perfect Night"),
    ("TWICE", "The Feels"), ("FIFTY FIFTY", "Cupid"),
    ("Burna Boy", "Last Last"), ("Central Cee", "Doja"),
    ("GloRilla", "F.N.F. (Let's Go)"), ("Latto", "Big Energy"),
    ("Lil Nas X", "Industry Baby"), ("Lil Nas X", "That's What I Want"),
    ("Jack Harlow", "Lovin On Me"), ("GAYLE", "abcdefu"),
    ("Em Beihold", "Numb Little Bug"), ("Steve Lacy", "Bad Habit"),
    ("Omar Apollo", "Evergreen"), ("Beabadoobee", "Glue Song"),
    ("Wet Leg", "Chaise Longue"), ("The Backseat Lovers", "Kilby Girl"),
    ("Mitski", "My Love Mine All Mine"), ("Boygenius", "Not Strong Enough"),
    ("Fred again..", "Delilah (pull me out of this)"), ("JVKE", "golden hour"),
    ("David Kushner", "Daylight"), ("Tate McRae", "exes"),
    ("Tate McRae", "you broke me first"), ("Reneé Rapp", "Not My Fault"),
    ("Chappell Roan", "Casual"), ("Katseye", "Gnarly"),
    ("Katseye", "Touch"), ("Kali Uchis", "Moonlight"),
    ("Kali Uchis", "telepatía"), ("girl in red", "we fell in love in october"),
    ("Gigi Perez", "Sailor Song"), ("Coyote Theory", "This Side of Paradise"),
    ("Coldplay", "My Universe"), ("Elton John", "Cold Heart (PNAU Remix)"),
    ("Elton John", "Hold Me Closer"), ("The Weeknd", "Cry For Me"),
    ("Drake", "Laugh Now Cry Later"), ("Metro Boomin", "Creepin'"),
    ("Don Toliver", "No Idea"), ("Future", "Life Is Good"),
    ("Lizzo", "2 Be Loved (Am I Ready)"), ("Nicky Youre", "Sunroof"),
    ("OneRepublic", "I Ain't Worried"), ("Post Malone", "I Like You (A Happier Song)"),
    ("NEIKED", "Better Days"), ("Doja Cat", "Get Into It (Yuh)"),
    ("Lil Nas X", "STAR WALKIN'"), ("Nicki Minaj", "Super Freaky Girl"),
    ("Marshmello", "Leave Before You Love Me"),
    ("Charlie Puth", "Light Switch"), ("Megan Thee Stallion", "Sweetest Pie"),
    ("Charlie Puth", "Left and Right"), ("Marshmello", "Numb"),
    ("The Kid LAROI", "THOUSAND MILES"), ("Ed Sheeran", "2step"),
    ("DVRST", "Close Eyes"), ("Tiesto", "Don't Be Shy"),
    ("Pink Sweat$", "At My Worst"), ("Justin Bieber", "Intentions"),
    ("Lost Frequencies", "Where Are You Now"), ("Sleepy Hallow", "2055"),
    ("Masked Wolf", "Astronaut In The Ocean"), ("Blxst", "Chosen"),
    ("Justin Bieber", "Lonely"), ("Post Malone", "One Right Now"),
    ("Maroon 5", "Beautiful Mistakes"), ("Justin Bieber", "Hold On"),
    ("Doja Cat", "You Right"), ("Lil Nas X", "MONTERO (Call Me By Your Name)"),
    ("Maroon 5", "Lost"), ("Shawn Mendes", "When You're Gone"),
    ("Doja Cat", "Need to Know"), ("Sam Smith", "Unholy"),
    ("Stephen Sanchez", "Until I Found You"), ("Elton John", "Cold Heart"),
    ("ROSÉ", "APT."), ("Lady Gaga", "Hold My Hand"),
    ("yung kai", "blue"), ("The Weeknd", "Timeless"),
    ("The Weeknd", "One Of The Girls"),
    ("The Weeknd", "Dancing In The Flames"), ("The Weeknd", "Popular"),
    ("Swedish House Mafia", "Moth To A Flame"), ("The Weeknd", "Sacrifice"),
    ("The Weeknd", "Out of Time"), ("Travis Scott", "FE!N"),
    ("Future", "Type Shit"), ("¥$", "CARNIVAL"),
    ("Ariana Grande", "we can't be friends (wait for your love)"), ("Ariana Grande", "34+35"),
    ("The Kid LAROI", "NIGHTS LIKE THIS"), ("The Kid LAROI", "BABY I'M BACK"),
    ("Ed Sheeran", "Shivers"), ("Ed Sheeran", "Eyes Closed"),
    ("Taylor Swift", "I Can Do It With a Broken Heart"), ("JVKE", "this is what falling in love feels like"),
    ("Selena Gomez", "People You Know"), ("The Chainsmokers", "Takeaway"),
    ("The Chainsmokers", "Hope"), ("David Guetta", "I Don't Wanna Wait"),
    ("OneRepublic", "Rescue Me"), ("OneRepublic", "Nobody"),
    ("OneRepublic", "Connection"), ("SZA", "Saturn"),
    ("Maroon 5", "Memories"), ("Imagine Dragons", "Enemy"),
    ("Imagine Dragons", "Bones"), ("Miley Cyrus", "Prisoner"),
    ("Dua Lipa", "Dance The Night"), ("David Guetta", "I'm Good (Blue)"),
    ("David Guetta", "Baby Don't Hurt Me"), ("Wiz Khalifa", "Hopeless Romantic"),
    ("¥$", "FIELD TRIP"), ("Baby Keem", "16"),
    ("Lil Mosey", "Blueberry Faygo"), ("Post Malone", "Cooped Up"),
    ("Future", "Young Metro"), ("Artemas", "cross my heart"),
    ("Gunna", "fukumean"), ("Drake", "What's Next"),
    ("Metro Boomin", "Too Many Nights"), ("Drake", "NOKIA"),
    ("Pop Smoke", "Mood Swings"), ("Lil Baby", "Life Goes On"),
    ("Future", "Cinderella"), ("Aaron Smith", "Dancin"),
    ("Lil Baby", "Stuff"), ("Young Thug", "Hot"),
    ("Internet Money", "Lemonade"), ("Masego", "Mystery Lady"),
    ("Young Thug", "Bad Bad Bad"), ("A$AP Rocky", "Everyday"),
    ("Lil Tecca", "Ransom"), ("Mustard", "Ballin'"),
    ("Metro Boomin", "Superhero (Heroes & Villains)"), ("Tommy Richman", "MILLION DOLLAR BABY"),
    ("Billie Eilish", "everything i wanted"), ("d4vd", "Feel It"),
    ("GIVEON", "Heartbreak Anniversary"), ("Lil Uzi Vert", "The Way Life Goes"),
    ("The Walters", "I Love You So"), ("Ravyn Lenae", "Love Me Not"),
    ("Dhruv", "double take"), ("Powfu", "death bed (coffee for your head)"),
    ("Future", "WAIT FOR U"), ("Future", "Solo"),
    ("The Weeknd", "After Hours"), ("THE ANXIETY", "Meet Me At Our Spot"),
    ("Twenty One Pilots", "Chlorine"), ("Lola Marsh", "Something Stupid"),
    ("BLACKPINK", "Pink Venom"), ("BLACKPINK", "How You Like That"),
    ("Stray Kids", "God's Menu"), ("Chappell Roan", "My Kink Is Karma"),
    ("Luke Combs", "Fast Car"),
    ("Don Toliver", "FWU"), ("Don Toliver", "No Pole"),
    ("Don Toliver", "NEW DROP"), ("Don Toliver", "Private Landing"),
    ("Don Toliver", "ICE AGE"), ("Don Toliver", "ATM"),
    ("Don Toliver", "PURPLE RAIN"), ("Yeat", "Nun id change"),
    ("Yeat", "PUT IT ONG"), ("Yeat", "LOCO"),
    ("Yeat", "If We Being Real"), ("Yeat", "COME N GO"),
    ("Travis Scott", "DUMBO"), ("Travis Scott", "TOPIA TWINS"),
    ("Travis Scott", "MAFIA"), ("Travis Scott", "ESCAPE PLAN"),
    ("Travis Scott", "2000 EXCURSION"), ("Travis Scott", "MY EYES"),
    ("Travis Scott", "FRANCHISE"), ("Travis Scott", "sweet sweet"),
    ("Gunna", "TOP FLOOR"), ("Gunna", "hakuna matata"),
    ("Metro Boomin", "Niagara Falls (Foot or 2)"), ("Metro Boomin", "Trance"),
    ("Ken Carson", "Yale"), ("Lil Tecca", "OWA OWA"),
    ("Trippie Redd", "KRZY TRAIN"), ("Rich Amiri", "ONE CALL"),
    ("Rich Amiri", "Paranoid"), ("PARTYNEXTDOOR", "DIE TRYING"),
    ("sosocamo", "keep steady"),
]

DECADE_WEIGHTS = {
    "1960s-70s": 0.4,
    "1980s": 0.5,
    "1990s": 0.7,
    "2000s": 1.0,
    "2010s": 1.7,
    "2020s": 1.9,
}

ERAS = ["1960s-70s", "1980s", "1990s", "2000s", "2010s", "2020s"]

# Genre is assigned per artist rather than per song: an artist's catalogue is
# overwhelmingly consistent in genre, and one lookup table is far easier to
# keep correct than 1,000+ individual tags. Artists are matched
# case-insensitively so casing variants ("Toto"/"TOTO") resolve the same.
GENRES = ["Pop", "Hip-Hop", "R&B", "Rock", "Indie", "Dance", "K-Pop"]

_GENRE_ARTISTS = {
    "Pop": [
        "*NSYNC", "ABBA", "Ace of Base", "Addison Rae", "Adele", "Air Supply",
        "Alessia Cara", "Alex Warren", "Alphaville", "Andy Grammer", "Anne-Marie",
        "Aqua", "Ariana Grande", "Artemas", "Backstreet Boys", "Bazzi", "Bee Gees",
        "Benson Boone", "Berlin", "Billie Eilish", "Bonnie Tyler", "Britney Spears",
        "Bruno Mars", "Camila Cabello", "Carly Rae Jepsen", "Celine Dion",
        "Chappell Roan", "Charli XCX", "Charlie Puth", "Cher", "Christina Aguilera",
        "Christina Perri", "Christopher Cross", "Colbie Caillat", "Culture Club",
        "Cyndi Lauper", "DNCE", "Daniel Powter", "Demi Lovato",
        "Dexys Midnight Runners", "Dido", "Doja Cat", "Dua Lipa", "Duran Duran",
        "Ed Sheeran", "Ed Sheeran & Justin Bieber", "Ellie Goulding", "Elton John",
        "Em Beihold", "Eurythmics", "Fergie", "Fifth Harmony", "Fools Garden",
        "Frank Sinatra", "Frankie Valli", "GAYLE", "Gavin DeGraw", "George Michael",
        "Gwen Stefani", "Halsey", "Harry Styles", "Hot Chelle Rae", "Iyaz", "JVKE",
        "James Arthur", "Jason Derulo", "Jason Mraz", "Jessie J", "John Newman",
        "Jon Bellion", "Jonas Brothers", "Justin Bieber", "Justin Timberlake",
        "Katrina & The Waves", "Katy Perry", "Kelly Clarkson", "Kesha", "Lady Gaga",
        "Lauv", "Lewis Capaldi", "Little Mix", "Lizzo", "Lorde", "Lukas Graham",
        "MAGIC!", "MKTO", "Madonna", "Mariah Carey", "Mark Ronson", "Maroon 5",
        "Meghan Trainor", "Michael Jackson", "Mike Posner", "Miley Cyrus",
        "Myles Smith", "Natalie Imbruglia", "Natasha Bedingfield", "Neil Diamond",
        "Nelly Furtado", "Niall Horan", "Nick Jonas", "Nicky Youre", "Nico & Vinz",
        "OMI", "Olivia Rodrigo", "One Direction", "OneRepublic", "Owl City", "P!nk",
        "Paul Anka", "Pharrell Williams", "Phil Collins", "Prince", "R. City",
        "Rachel Platten", "Reneé Rapp", "Rick Astley", "Rihanna", "Rixton",
        "Roxette", "Sabrina Carpenter", "Sam Smith", "Sara Bareilles",
        "Savage Garden", "Selena Gomez", "Selena Gomez & The Scene", "Shawn Mendes",
        "Sia", "Sixpence None The Richer", "Spice Girls", "Sub Urban", "Taio Cruz",
        "Tate McRae", "Taylor Swift", "Tears For Fears", "The Ronettes",
        "The Script", "The Wanted", "Toni Basil", "Tove Lo", "Train",
        "Vanessa Carlton", "Wham!", "Whitney Houston", "Why Don't We", "ZAYN",
        "a-ha", "benny blanco", "5 Seconds of Summer", "Julia Michaels",
        # Crossover hits kept after the Country/Latin purge — filed by how a
        # general audience encounters them rather than by the artist's home
        # genre, since those genres no longer exist here.
        "Carrie Underwood", "Luke Combs", "Luis Fonsi", "Shakira",
        "Post Malone", "The Kid LAROI", "Lil Nas X", "24kGoldn", "Flo Rida", "Pitbull", "Black Eyed Peas", "Gym Class Heroes", "Travie McCoy", "Silento", "Masked Wolf", "Powfu", "Tommy Richman",
        "Macklemore & Ryan Lewis", "Macklemore", "Jack Harlow",
    ],
    "Hip-Hop": [
        "2Pac", "A Boogie Wit da Hoodie", "A$AP Rocky", "B.o.B",
        "Baby Keem", "Beastie Boys", "Big Sean", "Blxst",
        "Cardi B", "Central Cee", "Coolio", "DJ Khaled", "Don Toliver", "Dr. Dre",
        "Drake", "Eminem", "Fetty Wap", "Future", "G-Eazy", "GloRilla",
        "Gunna", "Ice Spice", "Iggy Azalea", "Internet Money",
        "J. Cole", "JAY-Z", "Juice WRLD", "Kanye West",
        "Kendrick Lamar", "Kid Cudi", "Kodak Black", "Latto", "Lil Baby",
        "Lil Mosey", "Lil Tecca", "Lil Uzi Vert", "Meek Mill",
        "Megan Thee Stallion", "Metro Boomin", "Migos", "Missy Elliott", "Mustard",
        "Nicki Minaj", "Offset", "Playboi Carti", "Pop Smoke",
        "Roddy Ricch", "Run-D.M.C.", "Salt-N-Pepa",
        "Sleepy Hallow", "The Notorious B.I.G.",
        "Timbaland", "Travis Scott", "Wiz Khalifa",
        "XXXTENTACION", "Young Thug", "¥$", "Outkast",
        "Yeat", "Ken Carson", "Rich Amiri", "Trippie Redd", "PARTYNEXTDOOR",
        "Sheck Wes", "Tyga", "sosocamo",
    ],
    "R&B": [
        "Akon", "Alicia Keys", "Amy Winehouse", "Aretha Franklin", "Ashanti",
        "Beyoncé", "Bill Withers", "Boyz II Men", "Burna Boy", "CKay", "CeeLo Green",
        "Chic", "Chris Brown", "Ciara", "Daniel Caesar", "Deborah Cox", "Des'ree",
        "Destiny's Child", "Donna Summer", "Earth, Wind & Fire", "En Vogue",
        "Estelle", "Frank Ocean", "GIVEON", "Gnarls Barkley", "Grover Washington Jr.",
        "John Legend", "KC and the Sunshine Band", "Kali Uchis", "Khalid",
        "Kool & The Gang", "Marvin Gaye", "Masego", "Miguel", "Montell Jordan",
        "Mya", "Next", "Omar Apollo", "Otis Redding", "Pink Sweat$", "Ravyn Lenae",
        "Rema", "Robin Thicke", "SWV", "SZA", "Sisqo", "Steve Lacy", "Stevie Wonder",
        "TLC", "Teddy Swims", "The Jackson 5", "The Supremes", "The Weeknd",
        "Toni Braxton", "Tyla", "USHER",
    ],
    "Rock": [
        "3 Doors Down", "311", "4 Non Blondes", "AC/DC", "AWOLNATION", "Aerosmith",
        "Alanis Morissette", "Ambrosia", "Avril Lavigne", "Badfinger", "Billy Idol",
        "Billy Joel", "Blind Melon", "Blondie", "Blue Swede", "Bob Dylan", "Bon Jovi",
        "Boston", "Boys Like Girls", "Bryan Adams", "Caesars", "Chicago",
        "Chuck Berry", "Coldplay", "Creed", "Crowded House", "Cutting Crew",
        "David Bowie", "Def Leppard", "Devo", "Divinyls", "Don McLean",
        "Eagle-Eye Cherry", "Eagles", "Eddie Money", "Electric Light Orchestra",
        "Elvis Presley", "Europe", "Evanescence", "Everlast", "Fall Out Boy",
        "Fastball", "Fleetwood Mac", "Foreigner", "Garbage", "Genesis",
        "Good Charlotte", "Green Day", "Guns N' Roses", "Hoobastank",
        "Huey Lewis and the News", "INXS", "Imagine Dragons", "Jimmy Eat World",
        "Joan Jett & the Blackhearts", "Journey", "KALEO", "KISS", "Keane",
        "King Harvest", "Kings of Leon", "Led Zeppelin", "Lifehouse", "Linkin Park",
        "Lynyrd Skynyrd", "Marcy Playground", "Matchbox Twenty", "Men At Work",
        "Meredith Brooks", "My Chemical Romance", "New Radicals", "Nirvana",
        "No Doubt", "Oasis", "Panic! At The Disco", "Paramore", "Peter Gabriel",
        "Plain White T's", "Player", "Queen", "R.E.M.", "Red Hot Chili Peppers",
        "Redbone", "Rick Springfield", "Semisonic", "Sheryl Crow", "Simon & Garfunkel",
        "Simple Minds", "Simple Plan", "Smash Mouth", "Spin Doctors",
        "Steve Miller Band", "Steve Winwood", "Sublime", "Sugar Ray", "Sum 41",
        "Survivor", "TOTO", "Tal Bachman", "Talking Heads", "The All-American Rejects",
        "The Beach Boys", "The Beatles", "The Cars", "The Clash", "The Cranberries",
        "The Fray", "The Goo Goo Dolls", "The Killers", "The Outfield", "The Police",
        "The Proclaimers", "The Revivalists", "The Rolling Stones", "Third Eye Blind",
        "Tom Petty", "U2", "Uncle Kracker", "Van Halen", "Weezer", "Whitesnake",
        "X Ambassadors", "Yellowcard", "John Denver", "Rascal Flatts",
    ],
    "Indie": [
        "Alt-J", "American Authors", "Arctic Monkeys", "BORNS", "Bastille",
        "Beabadoobee", "Bon Iver", "Boygenius", "Cage The Elephant", "Capital Cities",
        "Chvrches", "Cigarettes After Sex", "Coyote Theory", "David Kushner", "Dhruv",
        "Djo", "Echosmith", "Empire Of The Sun", "Fitz and The Tantrums",
        "Florence + The Machine", "Foster The People", "George Ezra", "Gigi Perez",
        "Glass Animals", "Gorillaz", "Gotye", "Gracie Abrams", "Grouplove", "Hozier",
        "James Bay", "Joji", "KT Tunstall", "Kodaline", "Lana Del Rey", "Lola Marsh",
        "Lord Huron", "M83", "MGMT", "Mazzy Star", "Milky Chance", "Mitski",
        "Mumford & Sons", "Neon Trees", "Noah Kahan", "Of Monsters and Men",
        "Passenger", "Phillip Phillips", "Phoenix", "Portugal. The Man", "Pulp",
        "Radiohead", "Rag'n'Bone Man", "Rex Orange County", "Role Model", "SHAED",
        "She & Him", "Snow Patrol", "Sombr", "Stephen Sanchez", "THE ANXIETY",
        "TV Girl", "Tame Impala", "The 1975", "The Backseat Lovers", "The Lumineers",
        "The Neighbourhood", "The Smiths", "The Walters", "Tom Odell",
        "Twenty One Pilots", "Two Door Cinema Club", "Vance Joy", "Walk the Moon",
        "Wet Leg", "Wolf Alice", "d4vd", "fun.", "girl in red", "yung kai", "Blur",
    ],
    "Dance": [
        "Aaron Smith", "Avicii", "Breakbot", "Calvin Harris", "Clean Bandit",
        "DJ Snake", "DVRST", "Daft Punk", "David Guetta", "Disclosure", "Duck Sauce",
        "Fred again..", "Gesaffelstein", "Haddaway", "Jack Ü", "Kungs", "Kygo",
        "LMFAO", "Lipps Inc.", "Lost Frequencies", "Major Lazer", "Marshmello",
        "Martin Garrix", "Modjo", "NEIKED", "Noisestorm", "Swedish House Mafia",
        "Tiesto", "Village People", "Zedd", "The Chainsmokers", "Los Del Rio",
    ],
    "K-Pop": [
        "BLACKPINK", "BTS", "FIFTY FIFTY", "Jung Kook", "Katseye", "LE SSERAFIM",
        "NewJeans", "PSY", "ROSÉ", "SEVENTEEN", "Stray Kids", "TWICE",
    ],
}

ARTIST_GENRE = {
    artist.lower(): genre
    for genre, artists in _GENRE_ARTISTS.items()
    for artist in artists
}

DEFAULT_GENRE = "Pop"


def genre_for(artist):
    return ARTIST_GENRE.get(artist.lower(), DEFAULT_GENRE)


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
                "genre": genre_for(artist),
                "video_id": None,
                "cover": "",
                "resolved": False,
                "removed": False,
                "start_offset": 0.0,
                # Every new song lands in the review queue rather than straight
                # into rotation: its snippet start has to be checked by hand
                # before players can be asked to guess it.
                "approved": False,
            }
            changed = True
        else:
            if "decade" not in data[key]:
                data[key]["decade"] = decade  # backfill for entries saved before decades existed
                changed = True
            if "start_offset" not in data[key]:
                data[key]["start_offset"] = 0.0  # backfill for entries saved before offsets existed
                changed = True
            # Backfilled once, then left alone — a song approved at offset 0.0
            # (because 0.0 genuinely was the right start) must not get pushed
            # back into the queue on the next sync.
            if "approved" not in data[key]:
                data[key]["approved"] = data[key].get("start_offset", 0.0) > 0
                changed = True
            # Re-derived every sync rather than only backfilled once, so
            # corrections to the artist→genre table propagate to songs that
            # were already saved.
            expected_genre = genre_for(artist)
            if data[key].get("genre") != expected_genre:
                data[key]["genre"] = expected_genre
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
            if not video_id:
                # No valid YouTube match at all (not just a poor one) — leaving
                # this "resolved" would silently strand it unplayable forever,
                # since only unresolved entries ever get retried.
                entry["removed"] = True
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


def live_songs():
    """Songs eligible for rotation: resolved to a video, not removed, and
    signed off in the review queue."""
    return [s for s in get_all_songs()
            if s["video_id"] and not s.get("removed") and s.get("approved")]


def review_queue(limit=None):
    """Songs waiting to be checked, most-played decades first — reviewing a
    2020s song pays off sooner than a 1960s one, since the decade weighting
    means it comes up more often once it's live."""
    pending = [s for s in get_all_songs()
               if s["video_id"] and not s.get("removed") and not s.get("approved")]
    pending.sort(key=lambda s: (-DECADE_WEIGHTS.get(s.get("decade"), 1.0),
                                s["artist"], s["title"]))
    return pending if limit is None else pending[:limit]


def review_counts():
    playable = [s for s in get_all_songs() if s["video_id"] and not s.get("removed")]
    approved = sum(1 for s in playable if s.get("approved"))
    return {
        "pending": len(playable) - approved,
        "approved": approved,
        "playable": len(playable),
    }


def set_approved(song_id, approved=True):
    data = _load()
    if song_id not in data:
        raise KeyError(song_id)
    data[song_id]["approved"] = bool(approved)
    _save(data)
    return data[song_id]


def filter_counts(eras=None, genres=None):
    """Per-era/genre song counts for the filter UI, plus how many songs the
    caller's current selection actually matches (so the UI can show the
    effect of a combination, which per-axis counts alone can't express)."""
    songs = live_songs()
    era_counts = {e: 0 for e in ERAS}
    genre_counts = {g: 0 for g in GENRES}
    for s in songs:
        if s.get("decade") in era_counts:
            era_counts[s["decade"]] += 1
        g = s.get("genre") or DEFAULT_GENRE
        if g in genre_counts:
            genre_counts[g] += 1

    matching = songs
    if eras:
        matching = [s for s in matching if s.get("decade") in set(eras)]
    if genres:
        matching = [s for s in matching if (s.get("genre") or DEFAULT_GENRE) in set(genres)]

    return {
        "eras": [{"id": e, "count": era_counts[e]} for e in ERAS],
        "genres": [{"id": g, "count": genre_counts[g]} for g in GENRES],
        "total": len(songs),
        "matching": len(matching),
    }


def random_playable_song(eras=None, genres=None):
    """Pick a weighted-random playable song, optionally restricted by filters.

    An empty/None filter means "no restriction on this axis" rather than
    "match nothing" — a player who has toggled everything off on one axis
    clearly wants it ignored, not an unplayable game.
    """
    songs = live_songs()

    if eras:
        wanted = set(eras)
        narrowed = [s for s in songs if s.get("decade") in wanted]
        if narrowed:
            songs = narrowed
    if genres:
        wanted = set(genres)
        narrowed = [s for s in songs if (s.get("genre") or DEFAULT_GENRE) in wanted]
        # Only apply if something survives — otherwise a narrow era+genre combo
        # (say K-Pop in the 1960s) would dead-end the game instead of just
        # relaxing to the wider pool.
        if narrowed:
            songs = narrowed

    if not songs:
        raise IndexError("no playable songs")

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


def set_start_offset(song_id, offset):
    data = _load()
    if song_id not in data:
        raise KeyError(song_id)
    data[song_id]["start_offset"] = max(0.0, float(offset))
    _save(data)
    return data[song_id]
