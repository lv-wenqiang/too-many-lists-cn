# 使用 Option

特别眼尖的读者可能已经注意到，我们其实是重新发明了一个非常糟糕的
Option 版本：

```rust ,ignore
enum Link {
    Empty,
    More(Box<Node>),
}
```

Link 就是`Option<Box<Node>>`。当然，不用到处写`Option<Box<Node>>`是挺舒服的，
而且和`pop`不一样，我们并没有把它暴露给外部世界，所以也许没什么问题。
不过 Option 有一些*非常好用*的方法，而我们一直在手动自己实现它们。
我们就*别*这么干了，把所有东西都换成 Option。首先，我们先笨拙地来一遍，
只是把所有东西改名成用 Some 和 None：

```rust ,ignore
use std::mem;

pub struct List {
    head: Link,
}

// yay type aliases!
type Link = Option<Box<Node>>;

struct Node {
    elem: i32,
    next: Link,
}

impl List {
    pub fn new() -> Self {
        List { head: None }
    }

    pub fn push(&mut self, elem: i32) {
        let new_node = Box::new(Node {
            elem: elem,
            next: mem::replace(&mut self.head, None),
        });

        self.head = Some(new_node);
    }

    pub fn pop(&mut self) -> Option<i32> {
        match mem::replace(&mut self.head, None) {
            None => None,
            Some(node) => {
                self.head = node.next;
                Some(node.elem)
            }
        }
    }
}

impl Drop for List {
    fn drop(&mut self) {
        let mut cur_link = mem::replace(&mut self.head, None);
        while let Some(mut boxed_node) = cur_link {
            cur_link = mem::replace(&mut boxed_node.next, None);
        }
    }
}
```

这只算是稍微好了一点点，真正的大收获来自 Option 的那些方法。

首先，`mem::replace(&mut option, None)`是一个极其常见的惯用写法，
以至于 Option 干脆直接把它做成了一个方法：`take`。

```rust ,ignore
pub struct List {
    head: Link,
}

type Link = Option<Box<Node>>;

struct Node {
    elem: i32,
    next: Link,
}

impl List {
    pub fn new() -> Self {
        List { head: None }
    }

    pub fn push(&mut self, elem: i32) {
        let new_node = Box::new(Node {
            elem: elem,
            next: self.head.take(),
        });

        self.head = Some(new_node);
    }

    pub fn pop(&mut self) -> Option<i32> {
        match self.head.take() {
            None => None,
            Some(node) => {
                self.head = node.next;
                Some(node.elem)
            }
        }
    }
}

impl Drop for List {
    fn drop(&mut self) {
        let mut cur_link = self.head.take();
        while let Some(mut boxed_node) = cur_link {
            cur_link = boxed_node.next.take();
        }
    }
}
```

其次，`match option { None => None, Some(x) => Some(y) }`也是一个极其常见的
惯用写法，它被叫做`map`。`map`接受一个函数，在`Some(x)`里的`x`上执行它，
从而产生出`Some(y)`里的`y`。我们本可以正儿八经写一个`fn`再把它传给`map`，
但我们更想*就地*写出要做的事情。

做到这一点的办法是用*闭包*。闭包是匿名函数，还多了一项超能力：
它们可以引用闭包*外部*的局部变量！这让它们在做各种条件逻辑时超级好用。
我们唯一用到`match`的地方是`pop`，那就把它重写一下：

```rust ,ignore
pub fn pop(&mut self) -> Option<i32> {
    self.head.take().map(|node| {
        self.head = node.next;
        node.elem
    })
}
```

啊，好多了。我们来确认一下没有弄坏什么东西：

```text
> cargo test

     Running target/debug/lists-5c71138492ad4b4a

running 2 tests
test first::test::basics ... ok
test second::test::basics ... ok

test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured

```

太好了！接下来我们真正去改进代码的*行为*。
