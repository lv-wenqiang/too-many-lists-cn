# IntoIter

在 Rust 中，集合是通过*Iterator* trait 来迭代的。它比`Drop`要稍微复杂一点：

```rust ,ignore
pub trait Iterator {
    type Item;
    fn next(&mut self) -> Option<Self::Item>;
}
```

这里的新面孔是`type Item`。它声明了每一个 Iterator 的实现都有一个叫做 Item 的
*关联类型*。在这个场景下，它就是你调用`next`时它能吐出来的那个类型。

Iterator 之所以产出`Option<Self::Item>`，是因为这个接口把`has_next`和
`get_next`两个概念合二为一了。当你有下一个值时，你就产出`Some(value)`，
没有时就产出`None`。这让 API 整体上用起来和实现起来都更顺手、更安全，
同时避免了`has_next`和`get_next`之间冗余的检查和逻辑。妙啊！

遗憾的是，Rust（暂时）没有类似`yield`语句的东西，所以我们只能自己实现这套逻辑。
另外，每个集合其实都应该努力实现 3 种不同的迭代器：

* IntoIter - `T`
* IterMut - `&mut T`
* Iter - `&T`

其实我们已经具备了用 List 的接口来实现 IntoIter 所需的全部工具：
不停地调用`pop`就行了。因此，我们直接把 IntoIter 实现成 List 的一个
newtype 包装：


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

然后我们来写个测试：

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
