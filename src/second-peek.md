偷看

上次我们甚至没有费心去实施的一件事就是偷看。我们走吧
并做到这一点。我们只需要返回对中元素的引用
列表的头部（如果存在）。听起来很简单，让我们试试：

```rust ,ignore
pub fn peek(&self) -> Option<&T> {
    self.head.map(|node| {
        &node.elem
    })
}
```


```text
> cargo build

error[E0515]: cannot return reference to local data `node.elem`
  --> src/second.rs:37:13
   |
37 |             &node.elem
   |             ^^^^^^^^^^ returns a reference to data owned by the current function

error[E0507]: cannot move out of borrowed content
  --> src/second.rs:36:9
   |
36 |         self.head.map(|node| {
   |         ^^^^^^^^^ cannot move out of borrowed content


```

* 叹气*。现在怎么办，拉斯特？

Map按值获取`self` ，这将将Option移出它所在的内容。
以前这很好，因为我们只是`take`n出来了，但现在我们实际上
想把它留在原地。处理此问题的*正确*方法是使用
Option上的`as_ref`方法，其定义如下：

```rust ,ignore
impl<T> Option<T> {
    pub fn as_ref(&self) -> Option<&T>;
}
```

它将`Option<T>`降级为引用其内部的Option。我们可以
用显式匹配自己做，但*呃不*。这确实意味着我们
需要做一个额外的dereference来切断额外的间接，但是
谢天谢地， `.`运营商为我们处理了这个问题。


```rust ,ignore
pub fn peek(&self) -> Option<&T> {
    self.head.as_ref().map(|node| {
        &node.elem
    })
}
```

```text
cargo build

    Finished dev [unoptimized + debuginfo] target(s) in 0.32s
```

搞定了！

我们还可以使用`as_mut`创建此方法的*可变*版本：

```rust ,ignore
pub fn peek_mut(&mut self) -> Option<&mut T> {
    self.head.as_mut().map(|node| {
        &mut node.elem
    })
}
```

```text
> cargo build

```

EZ

别忘了测试一下：

```rust ,ignore
#[test]
fn peek() {
    let mut list = List::new();
    assert_eq!(list.peek(), None);
    assert_eq!(list.peek_mut(), None);
    list.push(1); list.push(2); list.push(3);

    assert_eq!(list.peek(), Some(&3));
    assert_eq!(list.peek_mut(), Some(&mut 3));
}
```

```text
cargo test

     Running target/debug/lists-5c71138492ad4b4a

running 3 tests
test first::test::basics ... ok
test second::test::basics ... ok
test second::test::peek ... ok

test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured

```

这很好，但我们并没有真正测试是否可以改变`peek_mut`返回值，不是吗？如果一个引用是可变的，但没有人改变它，我们真的测试过可变性吗？让我们尝试在这个`Option<&mut T>`上使用`map`来给出深刻的价值：

```rust ,ignore
#[test]
fn peek() {
    let mut list = List::new();
    assert_eq!(list.peek(), None);
    assert_eq!(list.peek_mut(), None);
    list.push(1); list.push(2); list.push(3);

    assert_eq!(list.peek(), Some(&3));
    assert_eq!(list.peek_mut(), Some(&mut 3));
    list.peek_mut().map(|&mut value| {
        value = 42
    });

    assert_eq!(list.peek(), Some(&42));
    assert_eq!(list.pop(), Some(42));
}
```

```text
> cargo test

error[E0384]: cannot assign twice to immutable variable `value`
   --> src/second.rs:100:13
    |
99  |         list.peek_mut().map(|&mut value| {
    |                                   -----
    |                                   |
    |                                   first assignment to `value`
    |                                   help: make this binding mutable: `mut value`
100 |             value = 42
    |             ^^^^^^^^^^ cannot assign twice to immutable variable          ^~~~~
```

QUERY LENGTH LIMIT EXCEEDED. MAX ALLOWED QUERY : 500 CHARS

```rust ,ignore
    #[test]
    fn peek() {
        let mut list = List::new();
        assert_eq!(list.peek(), None);
        assert_eq!(list.peek_mut(), None);
        list.push(1); list.push(2); list.push(3);

        assert_eq!(list.peek(), Some(&3));
        assert_eq!(list.peek_mut(), Some(&mut 3));

        list.peek_mut().map(|value| {
            *value = 42
        });

        assert_eq!(list.peek(), Some(&42));
        assert_eq!(list.pop(), Some(42));
    }
```

```text
cargo test

     Running target/debug/lists-5c71138492ad4b4a

running 3 tests
test first::test::basics ... ok
test second::test::basics ... ok
test second::test::peek ... ok

test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured

```

好得多
