# 基础

我们现在已经掌握了 Rust 的许多基础知识，所以很多简单的东西可以再来一遍。

构造函数还是可以直接复制粘贴：

```rust ,ignore
impl<T> List<T> {
    pub fn new() -> Self {
        List { head: None }
    }
}
```

`push`和`pop`在这里已经没什么意义了。取而代之，我们可以提供`prepend`和`tail`，
它们提供的大致是同样的功能。

先从 prepend 开始。它接受一个链表和一个元素，返回一个 List。跟可变链表的情形
一样，我们想造一个新节点，让旧链表作为它的`next`值。唯一新鲜的地方在于怎么*拿到*
那个 next 值，因为我们不被允许修改任何东西。

回应我们祈祷的是 Clone 特征。几乎每个类型都实现了 Clone，它提供了一种通用的方式，
仅凭一个共享引用就能得到一个“和这个一样的另一个”，且在逻辑上互不相干。它就像 C++
里的拷贝构造函数，只不过它永远不会被隐式调用。

Rc 尤其把 Clone 当作递增引用计数的方式。所以我们不是把一个 Box 移动进子链表，
而是直接克隆旧链表的头部。我们甚至不需要对 head 做匹配，因为 Option 暴露了一个
恰好能干我们想要的事情的 Clone 实现。

好了，试一把：

```rust ,ignore
pub fn prepend(&self, elem: T) -> List<T> {
    List { head: Some(Rc::new(Node {
        elem: elem,
        next: self.head.clone(),
    }))}
}
```

```text
> cargo build

warning: field is never used: `elem`
  --> src/third.rs:10:5
   |
10 |     elem: T,
   |     ^^^^^^^
   |
   = note: #[warn(dead_code)] on by default

warning: field is never used: `next`
  --> src/third.rs:11:5
   |
11 |     next: Link<T>,
   |     ^^^^^^^^^^^^^
```

哇，Rust 在字段到底有没有被用上这件事情上真是死板得要命。它看得出来，
没有任何使用者能真正观察到这些字段的使用！不过到目前为止，我们看起来还不错。

`tail`是这个操作在逻辑上的逆操作。它接受一个链表，返回去掉第一个元素后的整个
链表。这不过就是克隆链表里的*第二个*元素（如果它存在的话）。来试试这个：

```rust ,ignore
pub fn tail(&self) -> List<T> {
    List { head: self.head.as_ref().map(|node| node.next.clone()) }
}
```

```text
cargo build

error[E0308]: mismatched types
  --> src/third.rs:27:22
   |
27 |         List { head: self.head.as_ref().map(|node| node.next.clone()) }
   |                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ expected struct `std::rc::Rc`, found enum `std::option::Option`
   |
   = note: expected type `std::option::Option<std::rc::Rc<_>>`
              found type `std::option::Option<std::option::Option<std::rc::Rc<_>>>`
```

嗯，我们搞砸了。`map`期望我们返回一个 Y，而我们这里返回的是一个`Option<Y>`。
好在，这也是 Option 的另一个常见套路，我们只要用`and_then`就能返回一个 Option。

```rust ,ignore
pub fn tail(&self) -> List<T> {
    List { head: self.head.as_ref().and_then(|node| node.next.clone()) }
}
```

```text
> cargo build

```

很好。

既然有了`tail`，我们大概也该提供`head`，它返回指向第一个元素的引用。
这就是可变链表里的`peek`：

```rust ,ignore
pub fn head(&self) -> Option<&T> {
    self.head.as_ref().map(|node| &node.elem)
}
```

```text
> cargo build

```

不错。

功能已经够多了，可以测试一下了：


```rust ,ignore
#[cfg(test)]
mod test {
    use super::List;

    #[test]
    fn basics() {
        let list = List::new();
        assert_eq!(list.head(), None);

        let list = list.prepend(1).prepend(2).prepend(3);
        assert_eq!(list.head(), Some(&3));

        let list = list.tail();
        assert_eq!(list.head(), Some(&2));

        let list = list.tail();
        assert_eq!(list.head(), Some(&1));

        let list = list.tail();
        assert_eq!(list.head(), None);

        // Make sure empty tail works
        let list = list.tail();
        assert_eq!(list.head(), None);

    }
}
```

```text
> cargo test

     Running target/debug/lists-5c71138492ad4b4a

running 5 tests
test first::test::basics ... ok
test second::test::into_iter ... ok
test second::test::basics ... ok
test second::test::iter ... ok
test third::test::basics ... ok

test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured

```

完美！

Iter 也和我们可变链表里的那个一模一样：

```rust ,ignore
pub struct Iter<'a, T> {
    next: Option<&'a Node<T>>,
}

impl<T> List<T> {
    pub fn iter(&self) -> Iter<'_, T> {
        Iter { next: self.head.as_deref() }
    }
}

impl<'a, T> Iterator for Iter<'a, T> {
    type Item = &'a T;

    fn next(&mut self) -> Option<Self::Item> {
        self.next.map(|node| {
            self.next = node.next.as_deref();
            &node.elem
        })
    }
}
```

```rust ,ignore
#[test]
fn iter() {
    let list = List::new().prepend(1).prepend(2).prepend(3);

    let mut iter = list.iter();
    assert_eq!(iter.next(), Some(&3));
    assert_eq!(iter.next(), Some(&2));
    assert_eq!(iter.next(), Some(&1));
}
```

```text
cargo test

     Running target/debug/lists-5c71138492ad4b4a

running 7 tests
test first::test::basics ... ok
test second::test::basics ... ok
test second::test::iter ... ok
test second::test::into_iter ... ok
test second::test::peek ... ok
test third::test::basics ... ok
test third::test::iter ... ok

test result: ok. 6 passed; 0 failed; 0 ignored; 0 measured

```

谁说动态类型更简单来着？

（是那些蠢货说的）

注意，我们没法为这个类型实现 IntoIter 或 IterMut。我们只有对元素的共享访问权。
