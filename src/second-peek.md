# 查看

上一次我们压根没费心去实现的一件事就是查看（peek）。这回我们把它做了。
我们要做的只是返回一个指向链表头部元素的引用（如果它存在的话）。
听起来很简单，来试试：

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

*叹气*。这回又怎么了，Rust？

map 按值获取`self`，这会把 Option 从它所在的地方移出来。以前这没问题，
因为我们刚刚才用`take`把它取出来过；但现在我们其实是想让它留在原地。
处理这件事的*正确*方式是用 Option 上的`as_ref`方法，它的定义如下：

```rust ,ignore
impl<T> Option<T> {
    pub fn as_ref(&self) -> Option<&T>;
}
```

它把`Option<T>`降级成一个指向其内部的引用的 Option。我们本可以用一个显式的
match 自己来做，但*算了吧*。这确实意味着我们需要多做一次解引用来穿透多出来的
那层间接，不过谢天谢地，`.`运算符替我们处理了这件事。


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

搞定收工。

我们还可以用`as_mut`做出这个方法的*可变*版本：

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

轻松。

别忘了测试它：

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

这挺好，可是我们并没有真正测试过能不能修改`peek_mut`返回的那个值，对吧？如果一个引用是可变的却没人去改它，我们真的算测试过可变性了吗？我们来试试在这个`Option<&mut T>`上用`map`，往里面塞一个意味深长的值：

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

编译器抱怨说`value`是不可变的，可我们明明白白写的是`&mut value`啊，这是怎么回事？原来，把闭包的参数写成那样并不是在声明`value`是一个可变引用。相反，它构造了一个用来匹配闭包实参的模式；`|&mut value|`的意思是“这个实参是一个可变引用，但麻烦你把它指向的值拷贝到`value`里”。如果我们只写`|value|`，那么`value`的类型就会是`&mut i32`，我们也就真的能修改头部了：

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

好多了！
