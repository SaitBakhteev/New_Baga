import asyncio

async def f_1():
    print('Корутина 1')

async def f_2():
    print('Корутина 2')

async def main():
    await asyncio.gather(f_1(), f_2())

asyncio.run(main())

