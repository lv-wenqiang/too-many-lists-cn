# 基础

> **旁白：**本节里潜伏着一个根本性的错误，因为这正是本书的意义所在。不过一旦我们开始用`unsafe`，就有可能做错了事情却依然能编译通过、而且*看上去*还能正常工作。这个根本性错误将在下一节被揪出来。千万不要把本节的内容直接用到生产代码里！

好了，回到基础。我们要怎么构造我们的链表呢？

以前我们是这么做的：

```rust ,ignore
impl<T> List<T> {
    pub fn new() -> Self {
        List { head: None, tail: None }
    }
}
```

但我们现在不再给`tail`用 Option 了：

```text
> cargo build

error[E0308]: mismatched types
  --> src/fifth.rs:15:34
   |
15 |         List { head: None, tail: None }
   |                                  ^^^^ expected *-ptr, found 
   |                                       enum `std::option::Option`
   |
   = note: expected type `*mut fifth::Node<T>`
              found type `std::option::Option<_>`
```

我们*本可以*用 Option，但和 Box 不同，`*mut`本身*就是*可空的。这意味着它没法
从空指针优化中获益。因此我们将改用`null`来表示 None。

那我们怎么弄到一个空指针呢？办法有几个，不过我更喜欢用`std::ptr::null_mut()`。
你要是愿意，也可以写`0 as *mut _`，但那看起来实在太*脏*了。

```rust ,ignore
use std::ptr;

// defns...

impl<T> List<T> {
    pub fn new() -> Self {
        List { head: None, tail: ptr::null_mut() }
    }
}
```

```text
cargo build

warning: field is never used: `head`
 --> src/fifth.rs:4:5
  |
4 |     head: Link<T>,
  |     ^^^^^^^^^^^^^
  |
  = note: #[warn(dead_code)] on by default

warning: field is never used: `tail`
 --> src/fifth.rs:5:5
  |
5 |     tail: *mut Node<T>,
  |     ^^^^^^^^^^^^^^^^^^

warning: field is never used: `elem`
  --> src/fifth.rs:11:5
   |
11 |     elem: T,
   |     ^^^^^^^

warning: field is never used: `head`
  --> src/fifth.rs:12:5
   |
12 |     head: Link<T>,
   |     ^^^^^^^^^^^^^
```

*嘘*，编译器，我们马上就会用到它们了。

好了，我们继续来写`push`。这一次，我们不再在插入之后去抓一个
`Option<&mut Node<T>>`，而是直接抓一个指向 Box 内部的`*mut Node<T>`。
我们知道这么做在原理上是站得住脚的，因为 Box 的内容有着稳定的地址，
即便我们把 Box 搬来搬去也一样。当然，这并不*安全*，
因为如果我们把 Box 丢弃了，手里就会剩下一个指向已释放内存的指针。

怎么从一个普通指针造出原始指针呢？靠强制转换！如果一个变量被声明为原始指针，
那么普通引用就会被强制转换成它：

```rust ,ignore
let raw_tail: *mut _ = &mut *new_tail;
```

我们需要的信息都齐了。可以把代码大致翻译成之前那个引用版本的样子：

```rust ,ignore
pub fn push(&mut self, elem: T) {
    let mut new_tail = Box::new(Node {
        elem: elem,
        next: None,
    });

    let raw_tail: *mut _ = &mut *new_tail;

    // .is_null checks for null, equivalent to checking for None
    if !self.tail.is_null() {
        // If the old tail existed, update it to point to the new tail
        self.tail.next = Some(new_tail);
    } else {
        // Otherwise, update the head to point to it
        self.head = Some(new_tail);
    }

    self.tail = raw_tail;
}
```

```text
> cargo build

error[E0609]: no field `next` on type `*mut fifth::Node<T>`
  --> src/fifth.rs:31:23
   |
31 |             self.tail.next = Some(new_tail);
   |             ----------^^^^
   |             |
   |             help: `self.tail` is a raw pointer; 
   |             try dereferencing it: `(*self.tail).next`
```

啊？我们手里有一个指向 Node 的指针，为什么拿不到`next`字段？

在你使用原始指针的时候，Rust 有点混蛋。要访问原始指针的内容，
它坚持要我们手动解引用，因为这是个非常不安全的操作。那我们就照做：

```rust ,ignore
*self.tail.next = Some(new_tail);
```

```text
> cargo build

error[E0609]: no field `next` on type `*mut fifth::Node<T>`
  --> src/fifth.rs:31:23
   |
31 |             *self.tail.next = Some(new_tail);
   |             -----------^^^^
   |             |
   |             help: `self.tail` is a raw pointer; 
   |             try dereferencing it: `(*self.tail).next`
```

呜呜呜，运算符优先级。

```rust ,ignore
(*self.tail).next = Some(new_tail);
```

```text
> cargo build

error[E0133]: dereference of raw pointer is unsafe and requires 
              unsafe function or block

  --> src/fifth.rs:31:13
   |
31 |             (*self.tail).next = Some(new_tail);
   |             ^^^^^^^^^^^^^^^^^ dereference of raw pointer
   |
   = note: raw pointers may be NULL, dangling or unaligned; 
     they can violate aliasing rules and cause data races: 
     all of these are undefined behavior
```

这。不。该。这。么。难。

还记得我说过不安全 Rust 就像是安全 Rust 的 FFI 语言吗？编译器希望我们明确划出
在哪里做这种 FFI 调用。我们有两个选择。第一，我们可以把*整个*函数标记为 unsafe，
这样它就变成一个不安全 Rust 函数，只能在`unsafe`上下文中被调用。这不太好，
因为我们希望自己的链表用起来是安全的。第二，我们可以在函数内部写一个`unsafe`
块，用来划定 FFI 的边界。这样就等于声明整个函数是安全的。我们选后者：


```rust ,ignore
pub fn push(&mut self, elem: T) {
    let mut new_tail = Box::new(Node {
        elem: elem,
        next: None,
    });

    let raw_tail: *mut _ = &mut *new_tail;

    if !self.tail.is_null() {
        // Hello Compiler, I Know I Am Doing Something Dangerous And
        // I Promise To Be A Good Programmer Who Never Makes Mistakes.
        unsafe {
            (*self.tail).next = Some(new_tail);
        }
    } else {
        self.head = Some(new_tail);
    }

    self.tail = raw_tail;
}
```

```text
> cargo build
warning: field is never used: `elem`
  --> src/fifth.rs:11:5
   |
11 |     elem: T,
   |     ^^^^^^^
   |
   = note: #[warn(dead_code)] on by default
```

好耶！

挺有意思的是，到目前为止那居然是我们*唯一*不得不写 unsafe 块的地方。
我们到处都在摆弄原始指针，这是怎么回事？

事实证明，一碰到`unsafe`，Rust 就是个极度较真的规则律师。我们非常合理地希望把
安全 Rust 程序的集合最大化，因为那些程序我们能有把握得多。为了做到这一点，
Rust 小心翼翼地把不安全的表面积削到最小。注意，我们之前摆弄原始指针的所有其他
地方，要么是在给它们*赋值*，要么只是在看它们是不是空的。

只要你从不真的去解引用一个原始指针，*那些操作都是完全安全的*。你不过是在读写
一个整数罢了！你真正会因为原始指针而惹上麻烦的唯一时刻，就是你真的解引用它的
时候。所以 Rust 说*只有*那个操作是不安全的，其他一切都完全安全。

极度。较真。但技术上没错。

> **旁白：**在世界的另一端，一位硬件工程师感到脊背一凉 &mdash; 一定又有人在
坚称指针不过是整数了。她低头看了看自己那份新的硬件指针认证方案提案，
流下一滴眼泪。隔壁的编译器工程师毫无感觉 &mdash; 他们早就学会了永远穿着
厚毛衣。

只有一部分指针操作*真正*不安全，这引出了一个有趣的问题：虽然我们本该用`unsafe`
块来划定不安全的范围，但它实际上依赖于在这个块之外建立起来的状态。
甚至是在函数之外！

这就是我所说的不安全*污染*。只要你在一个模块里用了`unsafe`，
整个模块就被不安全性污染了。所有东西都必须写对，才能确保不安全代码所依赖的
全部不变式都得以维持。

这种污染之所以可控，是因为有*私有性*。在我们的模块之外，我们所有的结构体字段
都是完全私有的，所以别人没法以任意方式搞乱我们的状态。只要我们暴露出去的 API
的任何组合都不会导致糟糕的事情发生，那么在外部观察者看来，
我们所有的代码就都是安全的！说到底，这和 FFI 的情形没什么两样。
只要某个 python 数学库暴露的是安全接口，没人需要在乎它底下是不是调了 C。

总之，我们继续看`pop`，它基本上就是把引用版本原样搬过来：

```rust ,ignore
pub fn pop(&mut self) -> Option<T> {
    self.head.take().map(|head| {
        let head = *head;
        self.head = head.next;

        if self.head.is_none() {
            self.tail = ptr::null_mut();
        }

        head.elem
    })
}
```

我们再一次看到安全性依赖于状态的例子。如果我们在*这个*函数里没能把尾指针置空，
当下我们不会看到任何问题。然而后续对`push`的调用就会开始往那个悬垂的尾指针上
写东西了！

我们来测试一下：

```rust ,ignore
#[cfg(test)]
mod test {
    use super::List;
    #[test]
    fn basics() {
        let mut list = List::new();

        // Check empty list behaves right
        assert_eq!(list.pop(), None);

        // Populate list
        list.push(1);
        list.push(2);
        list.push(3);

        // Check normal removal
        assert_eq!(list.pop(), Some(1));
        assert_eq!(list.pop(), Some(2));

        // Push some more just to make sure nothing's corrupted
        list.push(4);
        list.push(5);

        // Check normal removal
        assert_eq!(list.pop(), Some(3));
        assert_eq!(list.pop(), Some(4));

        // Check exhaustion
        assert_eq!(list.pop(), Some(5));
        assert_eq!(list.pop(), None);

        // Check the exhaustion case fixed the pointer right
        list.push(6);
        list.push(7);

        // Check normal removal
        assert_eq!(list.pop(), Some(6));
        assert_eq!(list.pop(), Some(7));
        assert_eq!(list.pop(), None);
    }
}
```

这就是栈的那个测试，只是把预期的`pop`结果顺序颠倒了过来。我还在末尾加了几步，
用来确保`pop`里那种尾指针被破坏的情况不会发生。

```text
cargo test

running 12 tests
test fifth::test::basics ... ok
test first::test::basics ... ok
test fourth::test::basics ... ok
test fourth::test::peek ... ok
test second::test::basics ... ok
test fourth::test::into_iter ... ok
test second::test::into_iter ... ok
test second::test::iter ... ok
test second::test::iter_mut ... ok
test second::test::peek ... ok
test third::test::basics ... ok
test third::test::iter ... ok

test result: ok. 12 passed; 0 failed; 0 ignored; 0 measured
```

金星一枚！

> **旁白：**它来了……