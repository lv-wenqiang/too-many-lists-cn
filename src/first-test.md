# 测试

我们现在已经实现了`push`和`pop`，就可以测试我们的栈了！Rust和cargo把测试作为一个一级特性来实现，所以写起测试来会很轻松。我们需要做的只是写一个函数，然后用`#[test]`标记它。

通常在Rust社区中，我们会把测试代码放在它所测试的部分的附近。不过我们通常会为测试创建单独的命名空间，来让它不与“真正的”代码产生冲突。就像我们用`mod`来表明`first.rs`应该被包含在`lib.rs`中，可以使用`mod`来*内联的*创建一个新文件：


```rust ,ignore
// in first.rs

mod test {
    #[test]
    fn basics() {
        // TODO
    }
}
```

之后，我们通过`cargo test`调用它。

```text
> cargo test
   Compiling lists v0.1.0 (/Users/ADesires/dev/temp/lists)
    Finished dev [unoptimized + debuginfo] target(s) in 1.00s
     Running /Users/ADesires/dev/lists/target/debug/deps/lists-86544f1d97438f1f

running 1 test
test first::test::basics ... ok

test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
; 0 filtered out
```

好的，我们的什么都不做的测试通过了！我们来让它实际做些事吧。我们会使用`assert_eq!`宏来进行测试。这不是什么特殊的测试魔法。它所做的仅仅是比较你给它的两个值，并且让在它们不相等的情况下让程序panic。没错，你通过崩溃来指出测试中的失败！

```rust ,ignore
mod test {
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
        assert_eq!(list.pop(), Some(3));
        assert_eq!(list.pop(), Some(2));

        // Push some more just to make sure nothing's corrupted
        list.push(4);
        list.push(5);

        // Check normal removal
        assert_eq!(list.pop(), Some(5));
        assert_eq!(list.pop(), Some(4));

        // Check exhaustion
        assert_eq!(list.pop(), Some(1));
        assert_eq!(list.pop(), None);
    }
}
```

```text
> cargo test

error[E0433]: failed to resolve: use of undeclared type or module `List`
  --> src/first.rs:43:24
   |
43 |         let mut list = List::new();
   |                        ^^^^ use of undeclared type or module `List`


```

噢！因为我们做了一个新的模块，所以需要把List显式的导入进来才能使用它。

```rust ,ignore
mod test {
    use super::List;
    // everything else the same
}
```

```text
> cargo test

warning: unused import: `super::List`
  --> src/first.rs:45:9
   |
45 |     use super::List;
   |         ^^^^^^^^^^^
   |
   = note: #[warn(unused_imports)] on by default

    Finished dev [unoptimized + debuginfo] target(s) in 0.43s
     Running /Users/ADesires/dev/lists/target/debug/deps/lists-86544f1d97438f1f

running 1 test
test first::test::basics ... ok

test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
; 0 filtered out
```

好极了！

那个警告又是怎么回事呢……？我们清楚的在测试里用了List！

……但仅仅在测试的过程中！为了平息编译器（以及对库的使用者友好），我们应该指明test模块只会在运行测试的过程中编译。

```rust ,ignore
#[cfg(test)]
mod test {
    use super::List;
    // everything else the same
}
```

这就是关于测试的所有要点了！
