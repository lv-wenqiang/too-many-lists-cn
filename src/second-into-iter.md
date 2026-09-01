# IntoIter

在 Rust 中，集合通过 *Iterator* 特征进行迭代。 It's a bit 更多
complicated than `Drop`:

```rust ,ignore
pub trait Iterator {
    type Item;
    fn next(&mut self) -> Option<Self::Item>;
}
```

这个 新 kid on 这个 block here 是 `type Item`. 这 是 declaring that 每个
实现 of Iterator has an *associated type* 称为 Item. In 这 case,
这 是 这个 type that it 可以 spit 出 当 你 call `next`.

这个 reason Iterator yields `Option<Self::Item>` 是 因为 这个 interface
coalesces 这个 `has_next` and `get_next` concepts. When 你 have 这个 next 值,
你 yield
`Some(value)`, and 当 你 don't 你 yield `None`. 这 makes 这个
API generally 更多 ergonomic and 安全 to use and 实现, while avoiding
redundant checks and 逻辑 between `has_next` and `get_next`. 不错！

Sadly, Rust has nothing like a `yield` statement (yet), so we're going to have to
实现 这个 逻辑 ourselves. Also, there's 实际上 3 不同 kinds of
迭代器 每个 collection 应该 endeavour to 实现:

* IntoIter - `T`
* IterMut - `&mut T`
* Iter - `&T`

我们 实际上 已经 have 所有 这个 tools to 实现
IntoIter 使用 List's interface: 只是 call `pop` 反复 and 反复. As such, we'll
只是 实现 IntoIter as a newtype wrapper 周围 List:


```rust ,ignore
// Tuple structs are an alternative form of struct,
// useful for trivial wrappers around other types.
pub struct IntoIter<T>(List<T>);

impl<T> List<T> {
    pub fn into_iter(self) -> IntoIter<T> {
        IntoIter(self)
    }
}

impl<T> Iterator for IntoIter<T> {
    type Item = T;
    fn next(&mut self) -> Option<Self::Item> {
        // access fields of a tuple struct numerically
        self.0.pop()
    }
}
```

接下来写个测试：

```rust ,ignore
#[test]
fn into_iter() {
    let mut list = List::new();
    list.push(1); list.push(2); list.push(3);

    let mut iter = list.into_iter();
    assert_eq!(iter.next(), Some(3));
    assert_eq!(iter.next(), Some(2));
    assert_eq!(iter.next(), Some(1));
    assert_eq!(iter.next(), None);
}
```

```text
> cargo test

     Running target/debug/lists-5c71138492ad4b4a

running 4 tests
test first::test::basics ... ok
test second::test::basics ... ok
test second::test::into_iter ... ok
test second::test::peek ... ok

test result: ok. 4 passed; 0 failed; 0 ignored; 0 measured

```

不错！
