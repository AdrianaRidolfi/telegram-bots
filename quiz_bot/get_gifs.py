import random

yay_gif_urls = [
    'https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExbGY2NDNpdHJ2cGhsazZmbXVrYjA0Mnh1OGZ2amxhYXJnaWZwYnFueCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/7yORCExjS87Jk10xSU/giphy.gif',
    'https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExdjhvdWludm5veGh5aXFuNDAzbGVsbDV0bzA2dnJkdmU4aW14bzFseCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/JQFuCdFbQAbNaawknQ/giphy.gif',
    "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExanRueDZza3ljNHg0MGJnNDYyaGdpdjJlYnYxZDdhanhtZ3BkbHBiNSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/D2hncA3u88gmeCFeoh/giphy.gif",
    "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExdmFvZXRkNHByNzJoenp4OWV6OTkwZnhudXQ5MGRsc2wzcHh1Z3A0MyZlcD12MV9naWZzX3NlYXJjaCZjdD1n/3og0IuE1EjI5ZQzr3i/giphy.gif",
    "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3ajhraXdlY3k1OWV4a3ZsOXA4c3BkbnhvZjBlbWF5Y3NoMXNnN2t0OSZlcD12MV9naWZzX3NlYXJjaCZjdD1n/3NtY188QaxDdC/giphy.gif",
    "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3ajhraXdlY3k1OWV4a3ZsOXA4c3BkbnhvZjBlbWF5Y3NoMXNnN2t0OSZlcD12MV9naWZzX3NlYXJjaCZjdD1n/qUOlzZ2qwpnuDZoCkA/giphy.gif",
    "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExMWdoOW1xeHRiMjdmZzlyMXB3YnJnbTFheHR2NHRhYmV4d2dwY3VjZSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/ul1YXHSzBQQiFfkdH2/giphy.gif",
    "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExbnR2OHk2cDRxdWtyZWFyc2plMm50ejdhcTRkbTF2ZGtueTBhZHY0aCZlcD12MV9naWZzX3NlYXJjaCZjdD1n/BPJmthQ3YRwD6QqcVD/giphy.gif",
    "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExM2ZrZjFzY3NsdjE1ZTV2bjB2am01MHk1NDBmamtoMTd2MW53YjhmZCZlcD12MV9naWZzX3NlYXJjaCZjdD1n/tTc43DeTm2kkJTrI2G/giphy.gif",
    "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3eGRyY2I2NzI4amp6YjBiaGdxbGRocnIyenRtdTg2ZTZlMHB1d293diZlcD12MV9naWZzX3NlYXJjaCZjdD1n/l2JdVRfJozpjq70SA/giphy.gif",
    "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExeXMxNHdnYmd1ZTMwODVhbXNwdzJneHA1ODNha2p6MzIzcThrem5kMiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/FpKKILCKqNIgIE1GZf/giphy.gif",
    "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExeXMxNHdnYmd1ZTMwODVhbXNwdzJneHA1ODNha2p6MzIzcThrem5kMiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/VhWVAa7rUtT3xKX6Cd/giphy.gif",
    "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3MXBjZjVzYXJiYTk0NjNxdjN4eTd5OTBuNGkxbnRvbndycWc2YWZkayZlcD12MV9naWZzX3NlYXJjaCZjdD1n/3oEjI5VtIhHvK37WYo/giphy.gif",
    "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3NnFhY3Z0Y3FueWFpNWx4Mncza2FyejBwcXZpcTBlZm41Nzc4OWdnYSZlcD12MV9naWZzX3NlYXJjaCZjdD1n/oV66MEGU2oW0qunjAN/giphy.gif",
    "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExN2VvbWxtbDFhZm05YjZjN3E4dHh0c2RkOHk2cDdzc3N2N3gzNTV1MSZlcD12MV9naWZzX3NlYXJjaCZjdD1n/qIXVd1RoKGqlO/giphy.gif",
    "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExamhueGxiYzlvN2twcnIyd3NudHFwempleWdvbmZsbmJlamtobG9tOCZlcD12MV9naWZzX3NlYXJjaCZjdD1n/xT5LMHxhOfscxPfIfm/giphy.gif",
    "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExaWVvaGR3a2k0NWpycTdhbmN4dnN1aGxodzMxeGNlbTRucmF6ZGg2MyZlcD12MV9naWZzX3NlYXJjaCZjdD1n/d4uMMisS8f3x6F9ox8/giphy.gif",
    "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExeXd1dHlkZTg3d2thMHpwZTNnZjBzYzJpdDJvaDZycGNydDhrY2NidiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/26DOoDwdNGKAg6UKI/giphy.gif"
]

yikes_gif_urls = [
    "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExem53ajkzcmM2aWJuam9yc2FjcTl0cmE4MnBqdmwzN3RzdXhjdWszNiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/kD6GfKDucNyvyLgFtg/giphy.gif",
    "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExem53ajkzcmM2aWJuam9yc2FjcTl0cmE4MnBqdmwzN3RzdXhjdWszNiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/228WzCuRqsrO3DdUc2/giphy.gif",
    "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExczVpdzJ6bHgzMTVydjFoOGJhdG5iYmJmZzdoNjl6bWp2ZTY2MDBrdiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/MZAC7yfuKPSQ8kgFav/giphy.gif",
    "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExczVpdzJ6bHgzMTVydjFoOGJhdG5iYmJmZzdoNjl6bWp2ZTY2MDBrdiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/ge0VHLx5Tb2aGkIHtu/giphy.gif",
    "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExczVpdzJ6bHgzMTVydjFoOGJhdG5iYmJmZzdoNjl6bWp2ZTY2MDBrdiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/57MN9dLjLCV2JwtWlS/giphy.gif",
    "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExczVpdzJ6bHgzMTVydjFoOGJhdG5iYmJmZzdoNjl6bWp2ZTY2MDBrdiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/gn0NGwznwsRMc9s4YQ/giphy.gif",
    "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExNjR1Zjc2dWpwMjFtbTJydjhxemVoYWdpdWVremhnNDQxZG9meWJkbiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/80TEu4wOBdPLG/giphy.gif",
    "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExNjR1Zjc2dWpwMjFtbTJydjhxemVoYWdpdWVremhnNDQxZG9meWJkbiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/dB12mOQb99BwDlM83I/giphy.gif",
    "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExNjR1Zjc2dWpwMjFtbTJydjhxemVoYWdpdWVremhnNDQxZG9meWJkbiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/sG4PBWRjI4GSVCDXEq/giphy.gif",
    "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExNjR1Zjc2dWpwMjFtbTJydjhxemVoYWdpdWVremhnNDQxZG9meWJkbiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/WRMq4MMApzBeg/giphy.gif",
    "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3dDFic2psbDBycTd4czNpYXk1dnJsaXVrZWZwN29nd2cza3psMGQ3OCZlcD12MV9naWZzX3NlYXJjaCZjdD1n/NCE9migrL4u7XygaAE/giphy.gif"
]

def yay():
    return random.choice(yay_gif_urls)

def yikes():
    return random.choice(yikes_gif_urls)