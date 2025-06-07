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
    "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3NnFhY3Z0Y3FueWFpNWx4Mncza2FyejBwcXZpcTBlZm41Nzc4OWdnYSZlcD12MV9naWZzX3NlYXJjaCZjdD1n/oV66MEGU2oW0qunjAN/giphy.gif"
]

def yay():
    return random.choice(yay_gif_urls)
